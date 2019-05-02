from collections import OrderedDict

from flask import render_template, redirect, request, url_for, flash, \
    current_app, abort
from flask.ext.login import login_required, current_user
from sqlalchemy import or_, and_
from wtforms import StringField, SelectMultipleField, SelectField, BooleanField
from wtforms.validators import required, email
from wtforms_dynamic_fields import WTFormsDynamicFields

from . import submission
from .forms import PaperForm
from ... import db
from ...models import Paper, Author, User, Track, UserDoc, Conference
from ...utils.decorators import chair_required
from ...utils.email_operation import send_email
from ...utils.event_log import add_event
from ..paper.forms import WithdrawForm


# My Submission
# TODO currently filtering my papers by who uploaded them, do we want
# other authors to see this too?


@submission.route('/')
@login_required
def my_submissions():
    withdraw_form = WithdrawForm()
    if current_user.curr_conf_id == 1:
        # main conf is the current conf: show papers in all conferences
        # no track information is shown
        # get values from the search bar
        page = request.args.get('page', 1, type=int)
        papertitle = request.args.get('papertitle', '')
        author = request.args.get('author', '')
        conference_filter_id = request.args.get(
            'conference_filter_id', type=int)
        empty_flag = False
        if papertitle == '' and author == '' and conference_filter_id <= 1:
            # the search bar is empty
            q_1 = current_user.papers
            q_2 = current_user.uploaded_papers
            pagination = q_1.union(q_2).filter(Paper.status != 'Deleted'). \
                order_by(Paper.id.asc()).paginate(page, per_page=20,
                                                  error_out=False)
        else:  # some values from the search bar
            if author != '':  # author search field is not empty
                try:
                    first_name, last_name = author.split(' ')
                except ValueError:
                    first_name = author
                    last_name = author
            else:  # no value in author search field
                first_name = ''
                last_name = ''
            if conference_filter_id > 1:
                pagination = current_user.papers.filter_by(
                    conference_id=conference_filter_id).filter(
                    Paper.authors_list.any(or_(
                        Author.first_name.contains(first_name),
                        Author.last_name.contains(last_name)))).filter(
                    Paper.title.contains(papertitle)).order_by(
                        Paper.id.asc()).paginate(page,
                                                 per_page=20,
                                                 error_out=False)
            elif conference_filter_id <= 1:  # show all conference papers
                pagination = current_user.papers.filter(
                    Paper.authors_list.any(or_(
                        Author.first_name.contains(first_name),
                        Author.last_name.contains(last_name)))).filter(
                    Paper.title.contains(papertitle)).order_by(
                        Paper.id.asc()).paginate(page,
                                                 per_page=20,
                                                 error_out=False)
            if not pagination.total:
                pagination = current_user.papers.order_by(
                    Paper.id.asc()).paginate(page,
                                             per_page=20,
                                             error_out=False)
                empty_flag = True
        my_submissions = pagination.items
        return render_template('submission/submissions_my.html',
                               my_submissions=my_submissions,
                               pagination=pagination, papertitle=papertitle,
                               author=author,
                               conference_filter_id=conference_filter_id,
                               empty_flag=empty_flag,
                               pdf_url=current_app.config['PDF_URL'],
                               withdraw_form=withdraw_form)

    else:
        # a specific conference is the current conf
        # no pagination is needed given not many papers in each conf
        # track needs to be shown
        q_1 = current_user.papers
        q_2 = current_user.uploaded_papers
        my_submissions = q_1.union(q_2).filter(
            Paper.conference_id == current_user.curr_conf_id,
            Paper.status != 'Deleted').order_by(Paper.id.asc()).all()
        return render_template('submission/submissions_my.html',
                               my_submissions=my_submissions,
                               pdf_url=current_app.config['PDF_URL'],
                               withdraw_form=withdraw_form)


# All Submissions
@submission.route('/all')
@chair_required
def all_submissions():
    # Get the desired page from the URL.
    # For example, /submissions/all?page=3 gets the papers on page 3.
    page = request.args.get('page', 1, type=int)
    papertitle = request.args.get('papertitle', '')
    author = request.args.get('author', '')
    empty_flag = False

    if papertitle == '' and author == '':
        pagination = Paper.query.order_by(Paper.submitted_time.asc()).paginate(
            page, per_page=20, error_out=False)
        all_papers = pagination.items
        # papers = Paper.query.order_by(Paper.id.asc()).all()
    else:
        if author != '':
            try:
                first_name, last_name = author.split(' ')
            except ValueError:
                first_name = author
                last_name = author
        else:
            first_name = author
            last_name = author
        pagination = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
                                                                   Author.last_name.contains(last_name)))).filter(
            Paper.title.contains(papertitle)).order_by(Paper.submitted_time.asc()).paginate(page, per_page=20,
                                                                                            error_out=False)
        all_papers = pagination.items

        if not len(all_papers):
            pagination = Paper.query.order_by(Paper.submitted_time.asc()).paginate(
                page, per_page=20, error_out=False)
            all_papers = pagination.items
            # papers = Paper.query.order_by(Paper.id.asc()).all()
            empty_flag = True
    return render_template('submission/submissions_all.html',
                           all_papers=all_papers,
                           pagination=pagination, papertitle=papertitle,
                           author=author, empty_flag=empty_flag,
                           pdf_url=current_app.config['PDF_URL'])
    # pagination = Paper.query.order_by(Paper.submitted_time.asc()).paginate(
    #     page,
    #     per_page=10,
    #     error_out=False)

    # if (view_all is True):
    #     all_papers = Paper.query.all()
    # else:
    #     all_papers = pagination.items

    # return render_template('submission/submissions_all.html',
    #                        all_papers=all_papers, pagination=pagination)


@submission.route('/add', methods=['GET', 'POST'])
@login_required
def add_submission():
    """Add submission to current conf."""
    if request.args.get('conf_id', False):
        conference = Conference.query.get_or_404(request.args['conf_id'])
        if not current_user.is_joined_conference(conference):
            if current_user.can_join_conference(conference,
                                                check_joined=False):
                current_user.join_conference(conference)
            else:
                flash('Conference has ended, You cannot submit paper anymore',
                      'error')
                abort(403)
        current_user.set_conference_id(conference.id)
    conference = current_user.curr_conf
    if conference.id == 1:
        flash('You are not allowed to submit paper to \'Main\'', 'error')
        abort(403)
    # add submission type
    if conference.configuration.get('submission_types', False):
        setattr(PaperForm,
                'submission_type',
                SelectField('Submission type *',
                            coerce=str,
                            choices=[
                                (type, type) for type in
                                conference.configuration.get(
                                    'submission_types', ['']).split(',')]))
    else:
        # remove the submission_type
        if hasattr(PaperForm, 'submission_type'):
            delattr(PaperForm, 'submission_type')
    form = PaperForm()
    tracks = conference.tracks.filter_by(status=True).all()
    if len(tracks) == 1:
        form.track_id.choices = [(tracks[0].id, tracks[0].name)]
        hide_tracks = True
    else:
        form.track_id.choices = [
            (track.id, track.name) for track in tracks if not track.default]
        hide_tracks = False
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
    dynamic.add_validator('author_organization', required,
                          message='This field is required')
    dynamic.add_validator('author_country', required,
                          message='This field is required')
    if conference.submission_questions:
        for id, question in conference.submission_questions.items():
            if question['include'] is True and \
                    question.get('deleted', False) is False:
                if question['ques_type'] != 1:
                    dynamic.add_field(id, question['desc'], StringField)
                else:
                    # handle multi select
                    dynamic.add_field(id, question['desc'],
                                      SelectMultipleField,
                                      choices=[
                                      (option, option) for option in
                                      question['options']],
                                      coerce=str)
                if question['require']:
                    dynamic.add_validator(
                        id, required, message='This field is required')
    # if the submission is not open
    if not conference.configuration.get('submission_process'):
        return render_template('submission/submission_add.html',
                               form=form, user=current_user,
                               submission_closed=True,
                               endpoint='self_submission',
                               pdf_url=current_app.config['PDF_URL'],
                               hide_tracks=hide_tracks)

    if request.method == 'POST':
        form = dynamic.process(PaperForm, request.form)
        # get default track or non default default tracks
        if len(tracks) == 1:
            form.track_id.choices = [(tracks[0].id, tracks[0].name)]
        else:
            form.track_id.choices = [
                (track.id, track.name) for track in tracks
                if not track.default]
        if form.validate_on_submit():
            # print form.filename.data
            paper_file = UserDoc.query.filter(
                and_(UserDoc.id.in_(form.filename.data.split(',')[:-1]),
                     UserDoc.uploader_id == current_user.id)).all()
            if not paper_file:
                flash('Please add a file', 'error')
                return redirect(url_for('submission.add_submission'))
            else:
                custom_question_answer = OrderedDict()
                for id, question in conference.submission_questions.items():
                    custom_question_answer[id] = {
                        'answer':
                        form.__dict__.get(id + '_1').data if form.__dict__.get(
                            id + '_1') else '',
                        'ques_type': question['ques_type'],
                        'desc': question['desc']
                    }

                paper = Paper(filename=paper_file[0].filename,
                              uploader_id=current_user.id,
                              title=form.title.data,
                              abstract=form.abstract.data,
                              keywords=form.keywords.data,
                              comment=form.comment.data,
                              conference_id=conference.id,
                              track_id=form.track_id.data,
                              custom_question_answer=custom_question_answer)
                for doc in paper_file:
                    paper.files.append(doc)
                if conference.configuration.get('submission_types', False):
                    paper.submission_type = form.submission_type.data
                # Turn the dynamic form's data into a dict so we can iterate
                # over it easie
                form_dict = form.__dict__
                i = 1
                authors = []
                while form_dict.get('author_email_' + str(i)):
                    cur_email = form_dict.get('author_email_' + str(i)).data
                    send_email_flag = False
                    user = User.query.filter_by(email=cur_email).first()
                    if user and user.primary_id:
                        # add to primary account
                        user = user.primary_user
                    if user:
                        # check if user has reach maximum submissions
                        if conference.configuration.get(
                                'submission_limit'):
                            if not user.can_submit_paper(conference.id):
                                # delete paper object
                                db.session.delete(paper)
                                flash(user.full_name + ' has reached maximum \
                                      number of submissions', 'error')
                                return redirect(
                                    url_for('submission.add_submission'))
                        # user already existed
                        paper.authors.append(user)
                        authors.append(user.full_name)
                    else:
                        # add new user if the author doesn't exsit in database
                        pwd = User.generate_pwd()
                        user = User(email=cur_email,
                                    password=pwd,
                                    first_name=form_dict.get(
                                        'author_firstname_' + str(i)).data,
                                    last_name=form_dict.get(
                                        'author_lastname_' + str(i)).data,
                                    country=form_dict.get(
                                        'author_country_' + str(i)).data,
                                    website=form_dict.get(
                                        'author_website_' + str(i)).data,
                                    organization=form_dict.get(
                                        'author_organization_' + str(i)).data,
                                    confirmed=True
                                    )
                        try:
                            db.session.add(user)
                            db.session.commit()
                        except Exception as e:
                            db.session.rollback()
                            flash(e.message, 'error')
                            return redirect(
                                url_for('submission.add_submission'))
                        paper.authors.append(user)
                        send_email_flag = True
                        authors.append(user.full_name)
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
                                        'author_organization_' + str(i)).data)
                    paper.authors_list.append(author)
                    db.session.add(author)
                    if send_email_flag:
                        # new user
                        # join conference
                        user.join_conference(conference)
                        # send an email to inform the new user
                        if form_dict.get('author_sendnotification_' + str(i)):
                            send_email(cur_email,
                                       'A paper with you as an author has been \
                                       submitted',
                                       'email/new_account_coauthor',
                                       reply_to=current_user.email,
                                       user=user,
                                       title=form.title.data, password=pwd,
                                       conference=conference.name,
                                       paper_id=paper.id)
                            send_email_flag = False
                    else:
                        # check if joined conference
                        if not user.is_joined_conference(conference):
                            user.join_conference(conference)
                        # send email to inform author
                        if form_dict.get('author_sendnotification_' + str(i)):
                            send_email(cur_email,
                                       'A paper with you as an author has been \
                                       submitted',
                                       'email/submit_notification',
                                       reply_to=current_user.email,
                                       user=user,
                                       title=form.title.data,
                                       conference=conference.name,
                                       paper_id=paper.id)
                    i += 1
                authors = ', '.join(authors)
                if conference.configuration.get(
                        'submissions_notification'):
                    # send email to inform the chair and track chairs.
                    cur_track = Track.query.get_or_404(form.track_id.data)
                    all_chairs = conference.chairs + \
                        cur_track.track_chairs
                    for chair in all_chairs:
                        send_email(chair.email,
                                   '[' +
                                   conference.short_name.upper() +
                                   '] ' + 'A paper has been received',
                                   'email/submit_notification_chair',
                                   reply_to=current_user.email,
                                   chair=chair, authors=authors,
                                   title=form.title.data,
                                   conference=conference.name)
                try:
                    db.session.add(paper)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash(e.message, 'error')
                    return redirect(
                        url_for('submission.add_submission'))
                add_event(current_user.full_name +
                          '(' + str(current_user.id) + ')' +
                          ' submitted paper: (' + str(paper.id) + ') ' +
                          paper.title,
                          paper.to_json_log(),
                          conference_id=paper.conference_id,
                          paper_id=paper.id,
                          type='paper_new')

                flash('Upload Successful', 'success')
                return redirect(
                    url_for('paper.get_paper_info', paper_id=paper.id))
        else:
            flash(form.errors, 'error')
            return redirect(url_for('submission.add_submission'))
    return render_template('submission/submission_add.html',
                           form=form, user=current_user,
                           pdf_url=current_app.config['PDF_URL'],
                           submission_closed=False,
                           endpoint='self_submission',
                           hide_tracks=hide_tracks)
