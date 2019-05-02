# -*- coding: utf-8 -*-
"""Reivew module for conferency."""


from flask import render_template, redirect, request, url_for, flash, \
    current_app, jsonify, abort, make_response
from flask.ext.login import login_required, current_user
from sqlalchemy import or_
from collections import OrderedDict
from wtforms_dynamic_fields import WTFormsDynamicFields
from wtforms import StringField, SelectMultipleField
from wtforms.validators import required
from datetime import datetime
from app.utils.regex import check_name
from .forms import ReviewForm, ReviewRequestForm
from ...models import Paper, Review, Author, User, Permission, \
    DelegateReview, PaperStatus, JoinTrack
from ...utils.decorators import permission_required, chair_required
from ...utils.email_operation import send_email
from ...utils.event_log import add_event
from . import review
from ... import db


# Add Review
@review.route('/add', methods=['GET', 'POST'])
@login_required
def add_review():
    """Deprecaated."""
    return redirect(url_for('review.my_reviews'))
    # Code copy pasted from /review code.
    form = ReviewForm()
    # load all papers assigned to current user
    if current_user.curr_conf_id == 1:
        form.paper_select.choices = [
            (paper.id, paper.title)
            for paper in current_user.papers_reviewed if paper.is_reviewable()]
    else:
        form.paper_select.choices = [
            (paper.id, paper.title)
            for paper in
            current_user.papers_reviewed.filter_by(
                conference_id=current_user.curr_conf_id) if
            paper.is_reviewable()]
    custom_questions = OrderedDict()
    for k, v in current_user.curr_conf.review_questions.items():
        if v['include'] is True and v.get('deleted', False) is False:
            custom_questions[k] = v
    dynamic = WTFormsDynamicFields()
    for id, question in custom_questions.items():
        if question['ques_type'] != 1:
            dynamic.add_field(id, question['desc'], StringField)
        else:
            # handle multi select
            dynamic.add_field(id, question[
                'desc'], SelectMultipleField, choices=[(option, option) for option in question['options']], coerce=str)
        if question['require']:
            dynamic.add_validator(
                id, required, message='This field is required')
    if request.method == 'POST':
        form = dynamic.process(ReviewForm, request.form)
        if current_user.curr_conf_id == 1:
            form.paper_select.choices = [(paper.id, paper.title)
                                         for paper in current_user.papers_reviewed]
        else:
            form.paper_select.choices = [(paper.id, paper.title)
                                         for paper in current_user.papers_reviewed.filter_by(
                conference_id=current_user.curr_conf_id)]
        form.process(request.form)
        if form.validate_on_submit():
            paper = Paper.query.filter_by(id=form.paper_select.data).first()
            # get custom question answer
            custom_question_answer = OrderedDict()
            for id, question in custom_questions.items():
                custom_question_answer[id] = {
                    'answer': form.__dict__.get(id + '_1').data if form.__dict__.get(id + '_1') else "",
                    'ques_type': question['ques_type'],
                    'desc': question['desc']
                }
            # reviewer cannot review same paper more than once
            review = paper.reviews.filter_by(
                reviewer_id=current_user.id).first()
            if review is None:
                review = Review(paper_id=form.paper_select.data,
                                conference_id=paper.conference.id,
                                reviewer=current_user._get_current_object(),
                                evaluation=form.evaluation.data,
                                confidence=form.confidence.data,
                                review_body=form.review_body.data,
                                confidential_comments=form.confidential_remarks.data,
                                custom_question_answer=custom_question_answer)
                db.session.add(review)
                db.session.commit()
                add_event(current_user.first_name + ' ' + current_user.last_name +
                          ' submits a new review on paper ' + paper.title, review.to_json_log())
                # check review delegation
                delegation = DelegateReview.query.filter_by(paper_id=review.paper_id,
                                                            delegatee_id=current_user.id,
                                                            status='Accepted').first()
                if delegation:
                    delegation.review_id = review.id
                    delegation.status = 'Submitted'
                    db.session.add(delegation)
                    db.session.commit()
                flash("Review Submitted", 'success')
            else:
                # update review
                review.evaluation = form.evaluation.data
                review.confidence = form.confidence.data
                review.review_body = form.review_body.data
                review.confidential_comments = form.confidential_remarks.data
                review.custom_question_answer = custom_question_answer
                db.session.add(review)
                db.session.commit()
                add_event(current_user.first_name + ' ' + current_user.last_name +
                          ' updates the review on paper ' + paper.title, review.to_json_log())
                flash('Your review has been updated', 'warning')
        else:
            # print form.errors
            flash(form.errors, 'error')
    return render_template('review/review_add.html',
                           form=form,
                           pdf_url=current_app.config['PDF_URL'],
                           review_process=current_user.curr_conf.configuration.get('review_process'))


# Edit review
@review.route('/add/<paper_id>', methods=['GET', 'POST'])
@login_required
def edit_review(paper_id):
    """Add review for a paper."""
    # Code copy pasted from /review code.
    success_flag = False
    paper = Paper.query.get_or_404(paper_id)
    delegation_flag = paper.if_has_subreview(current_user)
    if not (paper.reviewers.filter_by(
            id=current_user.id).first() or delegation_flag):
        abort(403)
    # current_user can review the paper
    if current_user.curr_conf_id != paper.conference_id:
        current_user.set_conference_id(paper.conference_id)
    form = ReviewForm()
    custom_questions = OrderedDict()
    for k, v in current_user.curr_conf.review_questions.items():
        if v['include'] is True and v.get('deleted', False) is False:
            custom_questions[k] = v
    dynamic = WTFormsDynamicFields()
    for id, question in custom_questions.items():
        if question['ques_type'] != 1:
            dynamic.add_field(id, question['desc'], StringField)
        else:
            # handle multi select
            dynamic.add_field(
                id, question['desc'], SelectMultipleField,
                choices=[(option, option) for option in question['options']],
                coerce=unicode)
        if question['require']:
            dynamic.add_validator(
                id, required, message='This field is required')
    # form.process(request.form)
    if delegation_flag:
        review = Review.query.filter(
            Review.paper_id == paper_id,
            DelegateReview.delegator_id == current_user.id,
            DelegateReview.review_id == Review.id).first()
    else:
        review = paper.reviews.filter_by(reviewer_id=current_user.id).first()
    if review:
        form.evaluation.data = review.evaluation
        form.confidence.data = review.confidence
        form.review_body.data = review.review_body
        form.confidential_remarks.data = review.confidential_comments
    if request.method == 'POST':
        form = dynamic.process(ReviewForm, request.form)
        if form.validate_on_submit():
            custom_question_answer = OrderedDict()
            for id, question in custom_questions.items():
                custom_question_answer[id] = {
                    'answer': form.__dict__.get(id + '_1').data if
                    form.__dict__.get(id + '_1') else '',
                    'ques_type': question['ques_type'],
                    'desc': question['desc']
                }
            # reviewer cannot review same paper more than once
            paper = Paper.query.filter_by(id=paper_id).first()
            if not review:
                review_flag = 'submitted'
                review = Review(
                    paper_id=paper_id,
                    conference_id=paper.conference.id,
                    reviewer_id=current_user.id,
                    evaluation=form.evaluation.data,
                    confidence=form.confidence.data,
                    review_body=form.review_body.data,
                    confidential_comments=form.confidential_remarks.data,
                    custom_question_answer=custom_question_answer)
                db.session.add(review)
                # check review delegation
                delegation = DelegateReview.query.filter_by(
                    paper_id=review.paper_id, delegatee_id=current_user.id,
                    status='Accepted').first()
                if delegation:
                    delegation.review_id = review.id
                    delegation.status = 'Submitted'
                    db.session.add(delegation)
                try:
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash(e.message, 'error')
                    return redirect(url_for('review.edit_review',
                                            paper_id=paper_id))
                if delegation:
                    # send notification to delegator
                    send_email(
                        delegation.delegator.email,
                        current_user.full_name + ' submitted a new review',
                        'email/review_delegate_new_review',
                        reply_to=current_user.email,
                        paper=paper,
                        delegation_id=delegation.id)
            else:
                # update review
                review_flag = 'updated'
                review.evaluation = form.evaluation.data
                review.confidence = form.confidence.data
                review.review_body = form.review_body.data
                review.confidential_comments = form.confidential_remarks.data
                review.custom_question_answer = custom_question_answer
                db.session.add(review)
                db.session.commit()
            success_flag = True
            send_email(current_user.email,
                       'A review has been ' + review_flag,
                       'email/review_update',
                       paper=paper)
            add_event(current_user.full_name + '(' + str(current_user.id) +
                      ') ' + review_flag + ' the review on paper: (' +
                      str(paper.id) + ') ' + paper.title,
                      review.to_json_log(),
                      conference_id=paper.conference_id,
                      paper_id=paper.id,
                      review_id=review.id,
                      type='review_new' if review_flag == 'submitted' else
                      'review_update')
        else:
            flash('Problem Validating Form', 'error')
    # comments = ReviewComment.query.filter_by(review_id=review.id).order_by(
    #     ReviewComment.timestamp).all() if review else []
    return render_template('review/review_add.html',
                           form=form,
                           pdf_url=current_app.config['PDF_URL'],
                           configuration=paper.track.configuration if
                           paper.track.configuration.get(
                            'allow_review_config')
                           else paper.conference.configuration,
                           paper=paper, review=review,
                           delegation_flag=delegation_flag,
                           success_flag=success_flag,
                           # comments=comments,
                           current_time=datetime.utcnow(),
                           review_answer=review.custom_question_answer if
                           review else {})


@review.route('/download/<paper_id>', methods=['GET'])
@login_required
def download_form(paper_id):
    paper = Paper.query.filter_by(id=paper_id).first()
    author_str = ""
    for author in paper.authors_list:
        author_str += author.first_name + author.last_name + ", " + author.organization + "\n"
    custom_question_str = ""
    for key, item in paper.conference.review_questions.items():
        if item['include']:
            if item['ques_type'] == 0:
                custom_question_str += "(Single choice)" + item['desc']
                if item['require']:
                    custom_question_str += " *"
                custom_question_str += "\n\n" + "\tOptions:\n"
                for option in item['options']:
                    custom_question_str += "\t\t" + option + "\n"
                custom_question_str += "\n"
            elif item['ques_type'] == 1:
                custom_question_str += "(Multiple choice)" + item['desc']
                if item['require']:
                    custom_question_str += " *"
                custom_question_str += "\n\n" + "\tOptions:\n"
                for option in item['options']:
                    custom_question_str += "\t\t" + option + "\n"
                custom_question_str += "\n"
            elif item['ques_type'] == 2:
                custom_question_str += "(Single line textbox)" + item['desc']
                if item['require']:
                    custom_question_str += " *"
                custom_question_str += "\n\n"
            elif item['ques_type'] == 3:
                custom_question_str += "(Essay textbox)" + item['desc']
                if item['require']:
                    custom_question_str += " *"
                custom_question_str += "\n\n\n\n"
    content = "Review Form\n\n******************************\n\nPaper ID: " + str(paper_id) + "\nTitle: " + \
              paper.title + "\nConference: " + paper.conference.name + "\nTrack: " + \
              paper.track.name + "\n"
    if not paper.conference.configuration.get('hide_author', False):
        content = content + "Authors: \n" + author_str + "\n"
    content = content + "Abstract:\n" + paper.abstract + "\n\nKeywords:\n" + \
              paper.keywords + "\n\n******************************\n\nOverall Evaluation *\n\n\tOptions:\n\t\t" + \
              "Accept\n\t\tWeak Accept\n\t\tBorderline\n\t\tWeak Reject\n\t\tReject\n\n" + \
              "Reviewer Confidence *\n\n\tOptions:\n\t\tExpert\n\t\tHigh\n\t\tMedium\n\t\tLow\n\t\tNone\n\n" + \
              "Review *\n\n\n\nConfidential Remarks \n\n\n\n" + custom_question_str
    response = make_response(content)
    response.headers["Content-Disposition"] = "attachment; filename=Review Form.txt"
    return response


@review.route('/')
@login_required
def my_reviews():
    page = request.args.get('page', 1, type=int)
    papertitle = request.args.get('papertitle', '')
    author = request.args.get('author', '')
    if current_user.curr_conf_id == 1:
        conference_filter_id = request.args.get(
            'conference_filter_id', type=int)
        empty_flag = False
        if papertitle == '' and author == '':
            pagination = current_user.get_review_assignments.order_by(
                Paper.id.desc()).paginate(page, per_page=20, error_out=False)
        else:
            if author != '':  # some values from the search bar
                try:  # author search field is not empty
                    first_name, last_name = author.split(' ')
                except ValueError:
                    first_name = author
                    last_name = author
            else:  # no value in author search field
                first_name = ""
                last_name = ""
            # if conference_filter_id > 1:  # a specific conference is choose
            # in the dropdown
            pagination = current_user.papers_reviewed.filter(
                Paper.authors_list.any(
                    or_(Author.first_name.contains(first_name),
                        Author.last_name.contains(last_name)))) \
                .filter(Paper.title.contains(papertitle)).group_by(
                        Paper.conference_id).paginate(page,
                                                      per_page=20,
                                                      error_out=False)
            if not pagination.total:  # show all conference papers
                pagination = current_user.papers_reviewed.order_by(
                    Paper.id.asc()).paginate(page, per_page=20,
                                             error_out=False)
                empty_flag = True
        my_reviews_papers = pagination.items
        return render_template('review/reviews_my.html',
                               my_reviews_papers=my_reviews_papers,
                               pagination=pagination, papertitle=papertitle,
                               author=author,
                               conference_filter_id=conference_filter_id,
                               empty_flag=empty_flag,
                               pdf_url=current_app.config['PDF_URL'])

    else:
        # no pagination is needed given not many papers in each conf
        # track needs to be shown
        pagination = current_user.get_review_assignments.filter_by(
            conference_id=current_user.curr_conf_id).paginate(
            page, per_page=20, error_out=False)
        my_reviews_papers = pagination.items
        show_track = True if len(
            current_user.curr_conf.get_tracks.all()) > 0 else False
        return render_template('review/reviews_my.html',
                               pagination=pagination,
                               my_reviews_papers=my_reviews_papers,
                               pdf_url=current_app.config['PDF_URL'],
                               show_track=show_track)


# All Reviews
@review.route('/all')
@chair_required
def all_reviews():
    page = request.args.get('page', 1, type=int)
    papertitle = request.args.get('papertitle', '')
    author = request.args.get('author', '')
    empty_flag = False
    if papertitle == '' and author == '':
        pagination = Paper.query.order_by(Paper.id.asc()).paginate(
            page, per_page=100, error_out=False)
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
            Paper.title.contains(papertitle)).order_by(Paper.id.asc()).paginate(page, per_page=20, error_out=False)
        all_papers = pagination.items

        if not len(all_papers):
            pagination = Paper.query.order_by(Paper.id.asc()).paginate(
                page, per_page=20, error_out=False)
            all_papers = pagination.items
            # papers = Paper.query.order_by(Paper.id.asc()).all()
            empty_flag = True
    return render_template('review/reviews_all.html',
                           all_papers=all_papers, pagination=pagination, papertitle=papertitle,
                           author=author, empty_flag=empty_flag, pdf_url=current_app.config['PDF_URL'])
    # all_papers = Paper.query.all()
    # return render_template('review/reviews_all.html', all_papers=all_papers)


# Review decisions
@review.route('/decision', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def decision_review():
    if request.method == 'POST':
        paper_id = request.form.get('paper_id', -1)
        paper_status = request.form.get('paper_status')
        paper = Paper.query.get_or_404(paper_id)
        paper.status = paper_status
        db.session.add(paper)
        db.session.commit()
        return "Success", 200
    page = request.args.get('page', 1, type=int)
    papertitle = request.args.get('papertitle', '')
    author = request.args.get('author', '')
    status = request.args.get('status', '')
    sort = request.args.get('sort', '')
    empty_flag = False

    if papertitle == '' and author == '' and status == '' and sort == '':
        pagination = Paper.query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)
        papers = pagination.items
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

        if status == 'accepted':
            status_type = 'Accepted'
        elif status == 'rejected':
            status_type = 'Rejected'
        elif status == 'underreview':
            status_type = 'Under review'
        else:
            status_type = ''

        if sort == '1':
            pagination = Paper.query.filter(
                Paper.authors_list.any(
                    or_(Author.first_name.contains(first_name),
                        Author.last_name.contains(last_name)))
                ).filter(
                    Paper.title.contains(papertitle)).filter(
                        Paper.status.contains(status_type)).order_by(
                            Paper.avg_score.desc()).paginate(page,
                                                             per_page=20,
                                                             error_out=False)
            # papers = pagination.items
            # papers = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
            #                                                        Author.last_name.contains(last_name)))).filter(Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(Paper.avg_score.desc()).all()
        elif sort == '2':
            pagination = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
                                                                       Author.last_name.contains(last_name)))).filter(
                Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(
                Paper.avg_score.asc()).paginate(page, per_page=20, error_out=False)
            # papers = pagination.items
            # papers = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
            #                                                        Author.last_name.contains(last_name)))).filter(Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(Paper.avg_score.asc()).all()
        elif sort == '3':
            pagination = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
                                                                       Author.last_name.contains(last_name)))).filter(
                Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(
                Paper.status.desc()).paginate(page, per_page=20, error_out=False)
            # papers = pagination.items
            # papers = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
            #                                                        Author.last_name.contains(last_name)))).filter(Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(Paper.status.desc()).all()
        else:
            pagination = Paper.query.filter(Paper.authors_list.any(or_(Author.first_name.contains(first_name),
                                                                       Author.last_name.contains(last_name)))).filter(
                Paper.title.contains(papertitle)).filter(Paper.status.contains(status_type)).order_by(
                Paper.id.asc()).paginate(page, per_page=20, error_out=False)
        papers = pagination.items

        if not len(papers):
            pagination = Paper.query.order_by(Paper.id.asc()).paginate(
                page, per_page=20, error_out=False)
            papers = pagination.items
            # papers = Paper.query.order_by(Paper.id.asc()).all()
            empty_flag = True
    return render_template('review/review_decision.html', papers=papers, pagination=pagination, papertitle=papertitle,
                           author=author, status=status, sort=sort, empty_flag=empty_flag,
                           pdf_url=current_app.config['PDF_URL'])


# ***** review assignment *****

@review.route('/assignment/manual')
@chair_required
def assignment_manual():
    return redirect(url_for('review.my_reviews'))
    page = request.args.get('page', 1, type=int)
    papertitle = request.args.get('papertitle', '')
    author = request.args.get('author', '')
    empty_flag = False
    if papertitle == '' and author == '':
        pagination = Paper.query.order_by(Paper.id.asc()).paginate(
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
                                                                   Author.last_name.contains(last_name)))). \
            filter(Paper.title.contains(papertitle)).order_by(Paper.id.asc()). \
            paginate(page, per_page=20, error_out=False)
        all_papers = pagination.items

        if not len(all_papers):
            pagination = Paper.query.order_by(Paper.id.asc()).paginate(
                page, per_page=20, error_out=False)
            all_papers = pagination.items
            # papers = Paper.query.order_by(Paper.id.asc()).all()
            empty_flag = True
    return render_template('review/review_assignment.html',
                           all_papers=all_papers, pagination=pagination, papertitle=papertitle,
                           author=author, empty_flag=empty_flag, pdf_url=current_app.config['PDF_URL'])


# deprecated
# get reviewers list
@review.route('/autocomplete/reviewer')
@login_required
def autocomplete_reviewer():
    reviewer_query = request.args.get('query')
    paper = Paper.query.get_or_404(request.args.get('paper_id'))
    conference = paper.conference
    track_ids = [
        track.id for track in conference.tracks.filter_by(status=True).all()]
    matched_users = User.query.filter(JoinTrack.user_id == User.id,
                                      JoinTrack.track_id.in_(track_ids)).filter(or_(User.first_name.like(
                                          "%" + reviewer_query + "%"), User.last_name.like("%" + reviewer_query + "%"))).all()
    suggestions = [dict(value=usr.first_name,
                        data=dict(id=usr.id,
                                  name=usr.full_name,
                                  reviewed_count=len(
                                      usr.papers_reviewed.filter_by(conference_id=current_user.curr_conf_id).all()) + \
                                      len(DelegateReview.query.filter(
                                          DelegateReview.delegator_id == usr.id,
                                          DelegateReview.conference_id == current_user.curr_conf_id).all()),
                                  avatar=usr.gravatar(ize=60),
                                  organization=usr.organization,
                                  website=usr.website,
                                  country=usr.country,
                                  email=usr.email)) for usr in matched_users]
    suggestion_json = jsonify(suggestions=suggestions)
    return suggestion_json


# deprecated
# get the relationship between a user and a paper.
@review.route('/papers/<int:paper_id>/users/<int:user_id>')
def get_paper_user_relation(paper_id, user_id):
    # get this paper's author list
    paper = Paper.query.get_or_404(paper_id)
    authors = paper.authors.all()
    author_ids = [item.id for item in authors]
    # if this usr is one of the authors of the paper
    if user_id in author_ids:
        return 'author'
    user = User.query.get_or_404(user_id)
    if paper.get_bid(user) == 2:
        return 'bidding_2'
    # Only return the most important information first
    # get the co-author list
    author_papers = []
    coauthors = []
    for author in authors:
        author_papers += author.papers
    for coauthor_paper in author_papers:
        coauthors += coauthor_paper.authors
    # sort is not required, faster function might exist
    coauthor_ids = sorted(set([item.id for item in coauthors]))
    # if this usr is co-author of the authors of the paper
    if user_id in coauthor_ids:
        return 'coauthor'

    # get the users that from the same organization
    author_organizations = []
    for author in authors:
        if author.organization not in author_organizations:
            author_organizations.append(author.organization)
    author_organizations = sorted(set(author_organizations))
    user_organization = user.organization
    # if this usr is colleague of the authors of the paper
    if user_organization in author_organizations:
        return 'colleague'
    # if this usr has delegated to sub reviewers
    delegation = DelegateReview.query.filter(DelegateReview.delegator_id==user_id,
        DelegateReview.paper_id==paper_id, DelegateReview.status=='Accepted').first()
    if delegation is not None:
        return "delegated"
    # otherwise, user can be added as reviewer
    return 'otherwise'


@review.route('/reviewers/<int:paper_id>/remove_check/<int:reviewer_id>')
@permission_required(Permission.MANAGE_REVIEW)
def remove_check(paper_id, reviewer_id):
    review = Review.query.filter(Review.reviewer_id==reviewer_id, Review.paper_id==paper_id).first()
    if review is not None:
        return 'review exists'
    return 'safe to remove'


# deprecated
# assign reviewers backend
# TODO Change this so permissions are required to access reviewers
@review.route('/reviewers/<int:paper_id>', methods=['GET', 'POST', 'DELETE'])
@permission_required(Permission.MANAGE_REVIEW)
def reviewers(paper_id):
    """Operation on reviewers list."""
    if request.method == 'GET':
        paper = Paper.query.get_or_404(paper_id)
        reviewers = []
        for reviewer in paper.reviewers:
            reviewers.append(dict(first_name=reviewer.first_name,
                                  last_name=reviewer.last_name,
                                  id=reviewer.id))
        reviewer_json = jsonify(reviewers=reviewers)
        return reviewer_json
    elif request.method == 'POST':
        paper = Paper.query.filter_by(id=paper_id).first()
        for i in request.data.strip('[').strip(']').split(','):
            usr = User.query.filter_by(id=int(i.strip('"'))).first()
            paper.reviewers.append(usr)
        paper.status = PaperStatus.UNDER_REVIEW
        db.session.add(paper)
        db.session.commit()
        return "Success", 200
    elif request.method == 'DELETE':
        paper = Paper.query.filter_by(id=paper_id).first()
        for i in request.data.strip('[').strip(']').split(','):
            usr = User.query.filter_by(id=int(i)).first()
            paper.reviewers.remove(usr)
        db.session.add(paper)
        db.session.commit()
        return "Success", 200
    else:
        flash("Unsupported HTTP Verb", 'error')
        return redirect(url_for('main.dashboard'))


@review.route('/review_request/<int:paper_id>', methods=['GET', 'POST'])
@login_required
def review_request(paper_id):
    """Request a subreview."""
    # check user permission
    paper = Paper.query.get_or_404(paper_id)
    form = ReviewRequestForm()
    if not ((current_user in paper.reviewers.all() and current_user.is_pc(
            paper.conference) or current_user.is_chair(paper.conference) and
            paper.conference.configuration.get('allow_pc_chair_delegation',
                                               True)) or
            paper.get_subreviewer(current_user)):
        abort(403)
    else:
        delegation = paper.delegated_review_assignment.filter(
            DelegateReview.delegator_id == current_user.id,
            DelegateReview.status != 'Revoked',
            DelegateReview.status != 'Declined').first()
        if form.validate_on_submit():
            if delegation:
                # if pending delegation exists
                flash('Please revoke previous review request.', 'error')
                return redirect(url_for('review.review_request',
                                        paper_id=paper_id))
            user_existed = True
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.primary_id:
                # add to primary account
                user = user.primary_user
            if user is None:
                # new user
                pwd = User.generate_pwd()
                first_name, last_name = form.firstname.data, form.lastname.data
                if not check_name(last_name, first_name):
                    flash("The names are in wrong syntax.", 'error')
                else:
                    user = User(
                        email=form.email.data, first_name=form.firstname.data,
                        last_name=form.lastname.data, password=pwd,
                        confirmed=True)
                    db.session.add(user)
                    db.session.commit()
                    user_existed = False
            else:
                # user existed
                if user in paper.reviewers:
                    # if user is already a reviewer
                    flash('User is already one of the reviewers.', 'error')
                    return redirect(url_for('review.review_request',
                                            paper_id=paper_id))
                elif user in paper.authors:
                    # user is an author
                    flash('User is one of the authors.', 'error')
                    return redirect(url_for('review.review_request',
                                            paper_id=paper_id))
            content = form.content.data.replace(
                '*TITLE*', paper.title) \
                .replace('*CONFERENCE_NAME*', paper.conference.name) \
                .replace('*NAME*', form.firstname.data + ' ' +
                         form.lastname.data) \
                .replace('*FIRST_NAME*', form.firstname.data) \
                .replace('*LAST_NAME*', form.lastname.data)
            email_content = {
                'subject': form.subject.data,
                'content': content
            }
            if not user_existed:
                email_content['password'] = pwd
            if not DelegateReview.add_subreview(
                    current_user.id, user.id,
                    paper_id,
                    paper.conference_id,
                    email_content):
                flash('Database error', 'error')
            else:
                flash('Review request is sent.')
            return redirect(url_for('review.review_request',
                                    paper_id=paper_id))
        else:
            if delegation:
                form.firstname.data = delegation.delegatee.first_name
                form.lastname.data = delegation.delegatee.last_name
                form.email.data = delegation.delegatee.email
                form.subject.data = delegation.email_content['subject']
                form.content.data = delegation.email_content['content']
            else:
                form.subject.data = paper.conference.short_name.upper() + \
                    ' review request'
        # all delegations
        review_delegations = DelegateReview.query.filter(
            DelegateReview.delegator_id == current_user.id,
            DelegateReview.paper_id == paper.id).order_by(
            DelegateReview.timestamp.desc()).all()
        return render_template('review/review_request.html', form=form,
                               review_delegations=review_delegations,
                               paper=paper)


@review.route('/review_request/<int:delegation_id>/<string:operation>',
              methods=['GET', 'POST', 'PUT'])
@login_required
def review_request_operation(delegation_id, operation):
    """Revoke or resend review delegation."""
    delegation = DelegateReview.query.get_or_404(delegation_id)
    if delegation.status != 'Revoked':
        if current_user.id == delegation.delegator_id and \
            delegation.status != 'Approved' and \
                delegation.status != 'Submitted':
            # resend, revoked and approve
            paper = delegation.paper
            if operation == 'revoke':
                if delegation.status != 'Pending':
                    paper.reviewers.remove(delegation.delegatee)
                    paper.reviewers.append(delegation.delegator)
                    db.session.add(paper)
                delegation.status = 'Revoked'
                # send email to delegatee
            elif operation == 'resend':
                send_email(delegation.delegatee.email,
                           delegation.email_content.get('subject'),
                           'email/review_delegate_notification',
                           reply_to=delegation.delegator.email,
                           content=delegation.email_content,
                           delegation_id=delegation.id)
                return 'Success', 200
            else:
                abort(403)
            add_event(current_user.full_name + ' ' + operation +
                      ' the review request to ' +
                      delegation.delegatee.full_name,
                      delegation.to_json_log(),
                      conference_id=delegation.conference_id,
                      type='subreview_' + operation)
        else:
            abort(403)
        db.session.add(delegation)
        try:
            db.session.commit()
        except Exception as e:
            print(e)
            db.session.rollback()
        return 'Success', 200
    return render_template('review/review_request_operation.html')

# @review.route('/review_request', methods=['GET', 'POST'])
# @login_required
# def review_request_list():
#     review_delegations = DelegateReview.query.filter(DelegateReview.delegator_id == current_user.id,
#                                                      DelegateReview.paper_id == Paper.id,
#                                                      Conference.id == current_user.curr_conf_id,
#                                                      Paper.conference_id == Conference.id,
#                                                      DelegateReview.status != 'Revoked').order_by(DelegateReview.timestamp.desc()).all()
#     return render_template('review/review_request.html',
#                            review_delegations=review_delegations,
#                            endpoint='pc_review_request')
