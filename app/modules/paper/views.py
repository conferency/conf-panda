import os
from collections import OrderedDict
from datetime import datetime

from flask import render_template, redirect, request, url_for, flash, \
    current_app, send_file, abort, jsonify
from flask.ext.login import login_required, current_user
from wtforms import StringField, SelectMultipleField, SelectField, BooleanField
from wtforms.validators import required, email
from wtforms_dynamic_fields import WTFormsDynamicFields

from app.utils.regex import check_name
from . import paper
from .forms import WithdrawForm, PaperForm
from ... import db
from ... import uploaded_papers, uploaded_papers_with_docx, \
    uploaded_papers_without_pdf
from ...models import Paper, Author, User, UserDoc, PaperStatus, \
    UserDocStatus, discussant_paper_session
from ...utils.email_operation import send_email
from ...utils.event_log import add_event
from ...utils.s3_backup import send_to_s3


# show info of the paper after submitting
@paper.route('/info/<paper_id>', methods=['GET'])
@login_required
def get_paper_info(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    if not paper.if_has_access(current_user):
        abort(403)
    current_user.set_conference_id(paper.conference_id)
    # flag of the edit
    edit_flag = False
    if current_user in paper.authors:
        edit_flag = True
    show_all_submission = request.args.get('re', False)

    custom_question_answers = {}
    if paper.custom_question_answer:
        for ans_obj in paper.custom_question_answer.values():
            answer = ans_obj['answer']
            if answer:
                if isinstance(answer, list):
                    custom_question_answers[ans_obj['desc']] = ', '.join(
                        ans_obj['answer'])
                else:
                    custom_question_answers[ans_obj['desc']] = answer

    return render_template('paper/paper_info.html', paper=paper,
                           custom_question_answers=custom_question_answers,
                           edit_flag=edit_flag,
                           pdf_url=current_app.config['PDF_URL'],
                           show_all_submission=show_all_submission)


# edit the info of the paper
@paper.route('/edit/<paper_id>', methods=['GET', 'POST'])
@login_required
def edit_paper_info(paper_id):
    """Edit paper info."""
    paper = Paper.query.get_or_404(paper_id)
    # only author or uploader can edit paper
    conference = paper.conference
    allow_edit_author = False
    if current_user.curr_conf_id != conference.id:
        current_user.set_conference_id(conference.id)
    if not (current_user.id == paper.uploader_id or
            current_user in paper.authors or
            current_user.is_chair(conference)):
        flash('Only authors and uploader can edit this paper', 'error')
        abort(403)
    else:
        allow_edit_author = current_user.is_chair(
            conference) or conference.configuration.get(
                'allow_edit_paper_author')
        if conference.configuration.get('submission_types', False):
            setattr(PaperForm,
                    'submission_type',
                    SelectField('Submission type *',
                                coerce=str,
                                choices=[
                                    (type, type) for type in
                                    conference.configuration.get(
                                        'submission_types').split(',')],
                                default=paper.submission_type))
        else:
            # remove the submission_type
            if hasattr(PaperForm, 'submission_type'):
                delattr(PaperForm, 'submission_type')
        form = PaperForm()
        tracks = conference.tracks.filter_by(status=True).all()
        if len(tracks) == 1:
            form.track_id.choices = [
                (track.id, track.name) for track in tracks]
        else:
            form.track_id.choices = [
                (track.id, track.name) for track in tracks
                if not track.default]
        # withdraw_form = WithdrawForm()
        dynamic = WTFormsDynamicFields()
        dynamic.add_field('author_sendnotification', '', BooleanField)
        dynamic.add_field('author_email', 'Email *', StringField)
        dynamic.add_field('author_firstname', 'First Name *', StringField)
        dynamic.add_field('author_lastname', 'Last Name *', StringField)
        dynamic.add_field('author_organization', 'Organization *', StringField)
        dynamic.add_field('author_country', 'Country *', StringField)
        dynamic.add_field('author_website', 'Website', StringField)
        dynamic.add_validator('author_email', required,
                              message='This field is required')
        dynamic.add_validator('author_email', email,
                              message='This field is required')
        dynamic.add_validator('author_firstname', required,
                              message='This field is required')
        dynamic.add_validator('author_lastname', required,
                              message='This field is required')
        dynamic.add_validator('author_organization',
                              required, message='This field is required')
        dynamic.add_validator('author_country', required,
                              message='This field is required')
        for id, question in conference.submission_questions.items():
            if question['include'] is True and \
                    question.get('deleted', False) is False:
                if question['ques_type'] != 1:
                    dynamic.add_field(id, question['desc'], StringField)
                else:
                    # handle multi select
                    dynamic.add_field(
                        id,
                        question['desc'],
                        SelectMultipleField,
                        choices=[
                            (option, option) for option
                            in question['options']],
                        coerce=str)
                if question['require']:
                    dynamic.add_validator(
                        id, required, message='This field is required')
        if not paper.is_editable(current_user):
            return render_template('paper/paper_info_edit.html', form=form,
                                   user=current_user, paper=paper,
                                   pdf_url=current_app.config['PDF_URL'],
                                   submission_closed=True,
                                   allow_edit_author=allow_edit_author)
        if request.method == 'POST':
            form = dynamic.process(PaperForm, request.form)
            if len(tracks) == 1:
                form.track_id.choices = [
                    (track.id, track.name) for track in tracks]
            else:
                form.track_id.choices = [
                    (track.id, track.name) for track in tracks if
                    not track.default]
            if form.validate_on_submit():
                custom_question_answer = OrderedDict()
                for id, question in conference.submission_questions.\
                        items():
                    custom_question_answer[id] = {
                        'answer':
                            form.__dict__.get(id + '_1').data if
                            form.__dict__.get(id + '_1') else '',
                        'ques_type': question['ques_type'],
                        'desc': question['desc']
                    }
                # filename field now contains ALL papers
                if form.filename.data == '':
                    flash('There is no file for the paper!', 'error')
                    return redirect(
                        url_for('paper.edit_paper_info', paper_id=paper.id))

                new_docs = form.filename.data.split(',')[:-1]

                # files that can be seen by author and chairs
                files_on_record = paper.files.filter_by(
                    status=UserDocStatus.RECEIVED).all()
                for old_file in files_on_record:
                    if str(old_file.id) not in new_docs:
                        # if doc.uploader_id != current_user.id:
                        #     flash('You cannot delete file not uploaded by you',
                        #           'error')
                        #     return render_template(
                        #         'paper/paper_info_edit.html',
                        #         form=form, user=current_user,
                        #         paper=paper,
                        #         pdf_url=current_app.config['PDF_URL'],
                        #         submission_closed=False,
                        #         withdraw_form=withdraw_form)
                        # else:
                        old_file.status = UserDocStatus.DELETED
                        db.session.add(old_file)
                        # db.session.commit()

                paper_files = UserDoc.query.filter(
                    UserDoc.id.in_(new_docs)).all()

                for f in paper_files:
                    paper.files.append(f)

                # update the paper's title, abstract, keywords and comment
                paper.title = form.title.data
                paper.abstract = form.abstract.data
                paper.keywords = form.keywords.data
                paper.comment = form.comment.data
                if conference.configuration.get('submission_types',  False):
                    paper.submission_type = form.submission_type.data
                paper.custom_question_answer = custom_question_answer
                # Turn the dynamic form's data into a dict so we can iterate
                # over it easie
                form_dict = form.__dict__

                if allow_edit_author:
                    i = 1
                    while form_dict.get('author_email_' + str(i)):
                        first_name = form_dict.get(
                            'author_firstname_' + str(i)).data
                        last_name = form_dict.get(
                            'author_lastname_' + str(i)).data
                        if not check_name(first_name, last_name):
                            flash('Some fields have problems. Please check.',
                                  'error')
                            return render_template(
                                'paper/paper_info_edit.html',
                                form=form, user=current_user,
                                paper=paper,
                                pdf_url=current_app.config['PDF_URL'],
                                submission_closed=False,
                                allow_edit_author=allow_edit_author)
                        i += 1

                    # update the paper's author list
                    # empty the list first
                    paper.authors = []
                    paper.authors_list = []
                    i = 1
                    while form_dict.get('author_email_' + str(i)):
                        cur_email = form_dict.get(
                            'author_email_' + str(i)).data
                        user = User.query.filter_by(email=cur_email).first()
                        if user is not None:
                            if user.primary_id:
                                # add to primary account
                                user = user.primary_user
                            if conference.configuration.get(
                                    'submission_limit'):
                                if not user.can_submit_paper(conference.id):
                                    flash(user.full_name +
                                          ' has reached mixmum number of \
                                          submissions', 'error')
                                    return redirect(
                                        url_for('paper.edit_paper_info',
                                                paper_id=paper.id))
                            paper.authors.append(user)
                        else:
                            # add new user if the author doesn't exsit in
                            # database
                            pwd = User.generate_pwd()
                            first_name = form_dict.get(
                                "author_firstname_" + str(i)).data
                            last_name = form_dict.get(
                                "author_lastname_" + str(i)).data
                            user = User(email=cur_email,
                                        password=pwd,
                                        first_name=first_name,
                                        last_name=last_name,
                                        country=form_dict.get(
                                            'author_country_' + str(i)).data,
                                        website=form_dict.get(
                                            'author_website_' + str(i)).data,
                                        organization=form_dict.get(
                                            'author_organization_' + str(i)
                                            ).data,
                                        confirmed=True
                                        )
                            db.session.add(user)
                            db.session.commit()
                            paper.authors.append(user)
                            if form_dict.get(
                                    'author_sendnotification_' + str(i)):
                                send_email(cur_email,
                                           'A paper with you as an author has \
                                           been updated',
                                           'email/new_account_coauthor_update',
                                           reply_to=paper.uploader.email,
                                           user=user,
                                           title=form.title.data,
                                           password=pwd)
                        author = Author(email=cur_email,
                                        user_id=user.id,
                                        first_name=form_dict.get(
                                            'author_firstname_' + str(i)).data,
                                        last_name=form_dict.get(
                                            'author_lastname_' + str(i)).data,
                                        country=form_dict.get(
                                            'author_country_' + str(i)).data,
                                        website=form_dict.get(
                                            'author_website_' + str(i)).data,
                                        organization=form_dict.get(
                                            'author_organization_' + str(i)
                                            ).data)
                        paper.authors_list.append(author)
                        db.session.add(author)
                        # db.session.commit()
                        # send email to inform author
                        if form_dict.get("author_sendnotification_" + str(i)):
                            send_email(cur_email,
                                       'A paper with you as an author has been \
                                       updated',
                                       'email/update_notification',
                                       reply_to=paper.uploader.email,
                                       user=user,
                                       title=form.title.data,
                                       conference=conference.name)
                        i += 1
                # commit after loop
                paper.record_updated_time()

                try:
                    db.session.add(paper)
                    db.session.commit()
                except Exception:
                    db.session.rollback()
                    flash('Operation failed. Please try again or \
                          contact custom service',
                          'error')
                    return redirect(
                        url_for('paper.get_paper_info', paper_id=paper.id))
                flash('Successfully update paper information', 'info')
                add_event(current_user.full_name +
                          '(' + str(current_user.id) + ')' +
                          ' updated paper: (' + str(paper.id) + ') ' +
                          paper.title,
                          paper.to_json_log(),
                          conference_id=paper.conference_id,
                          paper_id=paper.id,
                          type='paper_update')
                return redirect(
                    url_for('paper.get_paper_info', paper_id=paper.id))
            else:
                flash(form.errors, 'error')
                return redirect(url_for('paper.edit_paper_info',
                                        paper_id=paper.id))
        # fill out the form
        form.title.data = paper.title
        form.abstract.data = paper.abstract
        form.keywords.data = paper.keywords
        form.comment.data = paper.comment
    return render_template('paper/paper_info_edit.html',
                           form=form, user=current_user, paper=paper,
                           submission_closed=False,
                           pdf_url=current_app.config['PDF_URL'],
                           allow_edit_author=allow_edit_author)


# download the paper
# @paper.route('/download/<paper_doc>', methods=['GET'])
# @login_required
# def get_pdf(paper_doc):
#     """Download paper file."""
#     paper_doc = UserDoc.query.
#     if not paper_doc:
#         abort(404)
#     # people who have access to the paper, administrators of this conference,
#     # authors, reviewers.
#     if not paper.is_downloadable(current_user):
#         return abort(403)
#     split_pack = paper_doc.split('_')
#     if len(split_pack) == 1:
#         paper_id = split_pack[0]
#     else:
#         paper_id, doc_id = split_pack
#     paper = Paper.query.get_or_404(paper_id)
#     if 'doc_id' in locals():
#         file_name = paper.files.filter_by(id=doc_id).first().filename
#     else:
#         file_name = paper.filename
#     try:
#         file_extension = file_name.split('.')[-1]
#         return send_file(current_app.config['PDF_URL'] + file_name,
#                          attachment_filename=paper.conference.short_name +
#                          '_paper_' + str(paper.id) + '.' + file_extension,
#                          as_attachment=True)
#     except IOError:
#         flash('Download failed, please contact supporting assistant',
#               'error')
#         return redirect(url_for('main.dashboard'))


@paper.route('/download_doc/<doc_id>', methods=['GET'])
@login_required
def get_doc(doc_id):
    """Download paper file. Used in Dropzone ONLY!"""
    if not doc_id:
        abort(404)

    _file = UserDoc.query.get_or_404(doc_id)

    file_name = _file.filename
    # people who have access to the paper, administrators of this conference,
    # authors, reviewers.
    if _file.uploader_id != current_user.id:
        return abort(403)
    else:
        try:
            file_extension = file_name.split('.')[-1]
            _name = 'not_submitted'
            if _file.paper_id:
                _name = str(_file.paper_id)
                return send_file(
                    current_app.config['PDF_URL'] + file_name,
                    attachment_filename=_file.paper.conference.short_name +
                    '_paper_' + _name + '.' + file_extension,
                    as_attachment=True)
            else:
                flash('Paper doesn\'t exist',
                      'error')
                return redirect(url_for('main.dashboard'))
        except IOError:
            flash('Download failed, please contact supporting assistant',
                  'error')
            return redirect(url_for('main.dashboard'))


@paper.route('/download/<int:paper_id>/<int:doc_id>', methods=['GET'])
@login_required
@paper.route('/pub_download/<int:paper_id>/<int:doc_id>',
             endpoint='public_get_doc')
def get_paper_doc(paper_id, doc_id):
    if (not paper_id) or (not doc_id):
        abort(404)
    paper = Paper.query.get_or_404(paper_id)
    doc = UserDoc.query.get_or_404(doc_id)
    file_name = doc.filename
    if paper.proceeding_included or paper.is_downloadable(current_user):
        try:
            file_extension = file_name.split('.')[-1]
            submission = file_name.split('.')[0].split('_')[-1]
            if submission != '':
                return send_file(
                    current_app.config['PDF_URL'] + file_name,
                    attachment_filename=paper.conference.short_name +
                    '_paper_' + str(paper.id) + '_submission_' + submission +
                    '.' + file_extension, as_attachment=True)
            else:
                return send_file(
                    current_app.config['PDF_URL'] + file_name,
                    attachment_filename=paper.conference.short_name +
                    '_paper_' + str(paper.id) + '.' + file_extension,
                    as_attachment=True)
        except IOError:
            flash('Download failed, please contact supporting assistant',
                  'error')
            return redirect(url_for('main.dashboard'))
    else:
        return abort(403)


@paper.route('/withdraw/<int:paper_id>', methods=['POST'])
@login_required
def paper_withdraw(paper_id):
    """Withdraw paper."""
    # may affect review delegation and notification
    withdraw_form = WithdrawForm()
    paper = Paper.query.get_or_404(paper_id)
    if current_user.id != paper.uploader_id:
        flash('Only the uploader of this paper can withdraw it.', 'error')
        return abort(403)
    if withdraw_form.validate_on_submit():
        paper.status = PaperStatus.WITHDRAWN
        paper.withdraw_reason = withdraw_form.message.data
        add_event('(' + str(current_user.id) + ') ' + current_user.full_name +
                  ' withdrew paper: (' + str(paper.id) + ') ' + paper.title,
                  {'message': withdraw_form.message.data},
                  conference_id=paper.conference_id,
                  paper_id=paper_id,
                  type='paper_withdraw')
        # sent out emails
        for author in paper.authors_list.all():
            send_email(author.email,
                       'Your paper \"' + paper.title + '\" has been withdrawn',
                       'email/paper_withdraw_notification',
                       reply_to=paper.uploader.email,
                       message=withdraw_form.message.data,
                       paper=paper,
                       receiver=author)
        for chair in paper.conference.chairs:
            send_email(chair.email, paper.conference.short_name.upper() +
                       ' - paper (' + str(paper.id) + ') \"' +
                       paper.title + '\" has been withdrawn',
                       'email/paper_withdraw_notification',
                       reply_to=paper.uploader.email,
                       message=withdraw_form.message.data,
                       paper=paper,
                       receiver=chair)
        for reviewer in paper.reviewers:
            if not paper.if_has_review(reviewer):
                paper.reviewers.remove(reviewer)
            send_email(reviewer.email, paper.conference.short_name.upper() +
                       ' - paper \"' + paper.title + '\" has been withdrawn',
                       'email/paper_withdraw_notification',
                       reply_to=paper.uploader.email,
                       paper=paper,
                       receiver=reviewer)
        try:
            db.session.add(paper)
            db.session.commit()
            flash('You have withdrawn ' + paper.title, 'info')
        except Exception:
            db.session.rollback()
            flash('Error! You have not withdrawn ' + paper.title, 'error')
    else:
        flash(withdraw_form.errors, 'error')
    return redirect(url_for('submission.my_submissions'))


# Paper Reviews
@paper.route('/<int:paper_id>/reviews', methods=['GET'])
@login_required
def paper_reviews(paper_id):
    """Reviews for the paper."""
    paper = Paper.query.get_or_404(paper_id)
    reviews = paper.get_reviews.all()
    if current_user in paper.authors or paper.sessions.filter(
            discussant_paper_session.c.user_id == current_user.id).first():
        return render_template('paper/paper_reviews.html',
                               role='author',
                               paper=paper, reviews=reviews,
                               pdf_url=current_app.config['PDF_URL'],
                               from_assignment=False,
                               current_time=datetime.utcnow(),
                               configuration=paper.track.configuration if
                               paper.track.configuration.get(
                                   'allow_review_config')
                               else paper.conference.configuration)
    elif current_user in paper.reviewers and \
            paper.conference.configuration.get('review_access', False):
        # the the corresponding review
        reviews = paper.get_reviews.filter_by(
            reviewer_id=current_user.id).all()
        return render_template('paper/paper_reviews.html',
                               paper=paper,
                               pdf_url=current_app.config['PDF_URL'],
                               reviews=reviews,
                               current_time=datetime.utcnow(),
                               configuration=paper.track.configuration if
                               paper.track.configuration.get(
                                   'allow_review_config')
                               else paper.conference.configuration,
                               from_assignment=False,
                               )
    elif current_user.is_chair(paper.conference):
        return render_template('paper/paper_reviews.html',
                               paper=paper,
                               pdf_url=current_app.config['PDF_URL'],
                               reviews=reviews,
                               current_time=datetime.utcnow(),
                               configuration=paper.track.configuration if
                               paper.track.configuration.get(
                                   'allow_review_config')
                               else paper.conference.configuration,
                               from_assignment=True)
    else:
        abort(403)


# # Not obvious how its used, but we use it in an <iframe> in pdf.html
@paper.route('/viewer')
@login_required
def viewer():
    return render_template('demos/viewer.html')


@paper.route('/uploadfile', methods=['GET', 'POST'])
@login_required
def uploadfile():
    """Upload paper api."""
    from flask.ext.uploads import UploadNotAllowed
    if current_user.curr_conf_id == 1:
        abort(403)
    folder = current_user.curr_conf.short_name
    papers = Paper.query.filter_by(
        conference_id=current_user.curr_conf_id).all()
    if papers is not None:  # not the first submission
        paper_number = len(papers) + 1
    else:  # first submission
        paper_number = 1
    file_name_base = folder + "-submission" + str(paper_number)
    if request.method == 'POST':
        docs = request.files.getlist('paper')
        for d in docs:
            if current_user.curr_conf.configuration.get(
                    'submission-word-allowed', False) and \
                    current_user.curr_conf.configuration.get(
                        'submission-pdf-allowed', True):
                up = uploaded_papers_with_docx
            elif current_user.curr_conf.configuration.get(
                    'submission-word-allowed', False):
                up = uploaded_papers_without_pdf
            elif current_user.curr_conf.configuration.get(
                    'submission-pdf-allowed', True):
                up = uploaded_papers
            if up.file_allowed(d, d.filename):
                try:
                    filename = up.save(
                        d,
                        folder=folder,
                        name=file_name_base + "." + d.filename.split(".")[-1])
                except UploadNotAllowed:
                    return 'This file is not allowed', 500
                else:
                    doc = UserDoc(
                        filename=filename, uploader_id=current_user.id)
                    db.session.add(doc)
                    db.session.commit()
                    if os.getenv('CONF_CONFIG') == 'production':
                        # send pdf to s3 if in production model
                        send_to_s3(doc.filename)
                    return jsonify(id=doc.id, filename=doc.filename), 201
            else:
                return 'This file is not a supported file-type', 500
                # return "Works"
        return "", 200
    else:
        files = UserDoc.query.filter_by(uploader_id=current_user.id).all()
        return render_template('paper/uploadfile.html', files=files)

# @paper.route("/removefile", methods=['DELETE'])
# @login_required
# def removefile():
#     doc_id = request.json.get('id')
#     if doc_id:
#         doc = UserDoc.query.get_or_404(doc_id)
#         if doc.uploader_id != current_user.id:
#             abort(403)
#         else:
#             db.session.delete(doc)
#             db.session.commit()
#             return "Success", 200
#     else:
#         abort(403)
