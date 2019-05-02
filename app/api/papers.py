# -*- coding: utf-8 -*-
"""API for papers."""

import os
from json import dumps
from flask import jsonify, request, current_app, json, Response, url_for
from flask_login import current_user
from yattag import Doc, indent
from .. import db
from ..models import Paper, Conference, User, Permission, DelegateReview, \
    PaperStatus, Author
from ..utils.event_log import add_event
from . import api
from .decorators import admin_required
from .errors import forbidden, bad_request
from .authentication import auth


# Returns the details of a single paper given an ID.
@api.route('/papers/<int:id>')
@auth.login_required
def get_paper(id):
    paper = Paper.query.get_or_404(id)
    return jsonify(paper.to_json())
    # return jsonify(paper.to_json()), 201, \
    #     {'Location': url_for('api.get_paper', id=paper.id, _external=True)}


@api.route('/papers/<int:id>', methods=['DELETE'])
@auth.login_required
def delete_paper(id):
    """Delete paper."""
    paper = Paper.query.get_or_404(id)
    if not current_user.can(
            (Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION),
            paper.conference):
        return forbidden('Not allowed')
    paper.status = PaperStatus.DELETED
    db.session.add(paper)
    db.session.commit()
    add_event(current_user.full_name + ' deleted paper: (' + str(paper.id) +
              ') ' + paper.title,
              paper.to_json_log(),
              conference_id=paper.conference_id,
              paper_id=paper.id,
              type='paper_delete')
    # send emails to notify authors, reviewers
    return jsonify(paper.to_json())


# Return relationship between a paper and a user. To further decide
# whether to select the user as reviewer.


@api.route('/conferences/<int:conference_id>/papers/<string:status>')
@auth.login_required
def get_papers(conference_id, status):
    conference = Conference.query.get_or_404(conference_id)
    # if status_code == 0:
    track_list = current_user.get_track_list(conference)
    papers = conference.papers.filter(
        Paper.status == status,
        Paper.track_id.in_(track_list)).all()
    # elif status_code == 1:
    # papers = conference.papers.filter_by(status='Accepted').all()
    # elif status_code == 2:
    #     papers = conference.papers.filter_by(status='Rejected').all()
    # elif status_code == 3:
    #     papers = conference.papers.filter_by(status='Under Review').all()

    return jsonify({'papers': [paper.to_json() for paper in papers]})


@api.route('/users/<int:id>/conferences/<int:conf_id>/papers_for_review')
@auth.login_required
def get_user_papers_for_review(id, conf_id):
    user = User.query.get_or_404(id)
    papers_for_review = user.get_review_assignments.filter(
        Paper.conference_id == conf_id).all()
    papers_with_missing_review = []
    papers_with_complete_review = []
    for paper in papers_for_review:
        if paper.reviews.filter_by(reviewer_id=user.id).first():
            papers_with_complete_review.append(paper)
        elif paper.delegated_review_assignment.filter(
                DelegateReview.delegator_id == user.id,
                DelegateReview.status == 'Approved').first():
            papers_with_complete_review.append(paper)
        else:
            papers_with_missing_review.append(paper)
    return jsonify({
        'reviewer': user.to_json(),
        'papers_for_review': [paper.to_json() for paper in papers_for_review],
        'papers_with_missing_review': [
            paper.to_json() for paper in papers_with_missing_review],
        'papers_with_complete_review': [
            paper.to_json() for paper in papers_with_complete_review],
        'conference_url': paper.conference.website,
        'conference_name': paper.conference.name,
    })


@api.route('/papers/<int:id>/track/change', methods=['POST'])
@auth.login_required
def change_track(id):
    """Change the track of a paper."""
    track_id = request.json['track_id']
    paper_id = request.json['paper_id']
    orig_track_id = request.json['orig_track_id']
    if str(paper_id) != str(id):
        return forbidden('Request dismatches the uri.')
    paper = Paper.query.get_or_404(paper_id)
    if str(paper.track_id) != str(orig_track_id):
        return forbidden('Original track id dismatches.')
    conf = paper.conference
    if not conf.tracks.filter_by(id=track_id).first():
        return forbidden('Track not in conference.')
    if current_user.can(Permission.MANAGE_REVIEW, conf):
        paper.track_id = track_id
        db.session.add(paper)
        db.session.commit()
        return 'Success', 200
    else:
        return forbidden('Insufficient permission.')


@api.route('/papers/<int:paper_id>/reviewers')
@auth.login_required
def get_paper_reviewers(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    conference = paper.conference
    user_list = set(
        conference.pcs + conference.chairs + conference.track_chairs)
    reviewers = [
        dict(value=usr.full_name,
             data=dict(id=usr.id,
                       name=usr.full_name,
                       reviewed_count=len(
                           usr.papers_reviewed.filter_by(
                               conference_id=current_user.curr_conf_id).all()),
                       organization=usr.organization,
                       email=usr.email)) for usr in user_list]
    reviewers_json = jsonify(reviewers=reviewers)
    return reviewers_json


@api.route('/papers/<int:paper_id>', methods=['PUT'])
@auth.login_required
def edit_paper(paper_id):
    """Edit paper."""
    paper = Paper.query.get_or_404(paper_id)
    # permission check
    if not paper.is_editable(current_user):
        return bad_request('No permission')
    if request.json:
        paper.title = request.json.get('title', paper.title)
        paper.proceeding_included = request.json.get('proceeding_included',
                                                     paper.proceeding_included)
        paper.status = request.json.get('status', paper.status)
        paper.abstract = request.json.get('abstract', paper.abstract)
        paper.keywords = request.json.get('keywords', paper.keywords)
        paper.submission_type = request.json.get('submission_type',
                                                 paper.submission_type)
        paper.comment = request.json.get('comment', paper.comment)
        paper.label = request.json.get('label', paper.label)
        try:
            db.session.add(paper)
            db.session.commit()
            return 'Success', 200
        except Exception as e:
            db.session.rollback()
            return bad_request(e.message)
    else:
        return bad_request('Unacceptable data.')


@api.route('/conferences/<int:conference_id>/papers/', methods=['POST'])
@admin_required
def import_papers(conference_id):
    """Import papers."""
    conference = Conference.query.get_or_404(conference_id)
    with open(os.path.join(current_app.config['UPLOADED_PAPERS_DEST'],
                           conference.short_name,
                           'paper_json.json')) as paper_json_file:
        paper_json = json.load(paper_json_file)
        for paper_info in paper_json:
            if not conference.papers.filter_by(
                    title=paper_info['title']).first():
                paper = Paper(
                    status=PaperStatus.ACCEPTED if
                    paper_info['status'] == 'ACCEPT' else PaperStatus.REJECTED,
                    title=paper_info['title'],
                    keywords=','.join(paper_info['keywords']),
                    abstract=paper_info['abstract'],
                    conference_id=conference_id,
                    track_id=conference.tracks.filter_by(
                        default=True).first().id,
                    uploader_id=current_user.id)
                for author in paper_info['authors']:
                    user = User.query.filter_by(email=author['email']).first()
                    if not user:
                        pwd = User.generate_pwd()
                        user = User(email=author['email'],
                                    first_name=author['first_name'],
                                    last_name=author['last_name'],
                                    organization=author['organization'],
                                    country='United States' if
                                    author['country'] == 'USA' else
                                    author['country'],
                                    website=author['website'],
                                    password=pwd)
                        db.session.add(user)
                        db.session.commit()
                    paper.authors.append(user)
                    author = Author(email=author['email'],
                                    user_id=user.id,
                                    first_name=author['first_name'],
                                    last_name=author['last_name'],
                                    country=user.country,
                                    website=author['website'],
                                    organization=author['organization'])
                    paper.authors_list.append(author)
                    db.session.add(author)
                    if not user.is_joined_conference(
                            conference):
                        user.join_conference(conference)
                db.session.add(paper)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return bad_request(e.message)
        return 'Success', 201


@api.route('/get_submissions/<int:conference_id>/<string:status>')
@auth.login_required
def get_submissions(conference_id, status):
    """Return all submissions."""
    conference = Conference.query.get_or_404(conference_id)
    tracks_list = conference.get_tracks.all()
    if not current_user.can(
            (Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION),
            conference):
        return forbidden('Not allowed')
    if status == 'Normal':
        papers = Paper.query.filter(
            Paper.conference_id == conference_id,
            ~Paper.status.in_(
                [PaperStatus.WITHDRAWN, PaperStatus.DELETED])).all()
    elif status in [PaperStatus.WITHDRAWN, PaperStatus.DELETED]:
        papers = Paper.query.filter(
            Paper.conference_id == conference_id,
            Paper.status == status).all()
    else:
        return bad_request('Status not allowed')
    submission_list = []
    for paper in papers:
        authors, tag, text, line = Doc().ttl()
        with tag('div'):
            for author in paper.authors_list.all():
                line('a', author.full_name,
                     klass='text-info',
                     style='padding-right:0.7em',
                     href=url_for('main.user', id=author.user_id))
        submitted_by, tag, text, line = Doc().ttl()
        with tag('div'):
            line('a', paper.uploader.full_name,
                 klass='text-info',
                 href=url_for('main.user', id=paper.uploader.id))
        review_button, tag, text, line = Doc().ttl()
        with tag('a', klass='btn-white btn-sm review',
                 id='review-' + str(paper.id),
                 href=url_for('paper.paper_reviews', paper_id=paper.id)):
            line('i', '', klass='fa fa-list-ul')
            text(' View reviews')
        tracks, tag, text, line = Doc().ttl()
        with tag('select',
                 ('data-paper-id', str(paper.id)),
                 ('data-paper-name', paper.title),
                 ('data-orig-track-id', str(paper.track_id)),
                 id='search_type', name='search_type',
                 klass='form-control track-selector'):
            if tracks_list:
                for track in tracks_list:
                    if track.id == paper.track_id:
                        line('option', track.name, value=str(track.id),
                             selected="selected")
                    else:
                        line('option',
                             track.name,
                             value=str(track.id))
        files, files_tag, files_text, files_line = Doc().ttl()
        deleted, deleted_tag, deleted_text, deleted_line = Doc().ttl()
        for file in paper.files.all():
            if file.status == 'Deleted':
                with deleted_tag('a',
                                 ('data-paperid', str(file.paper_id)),
                                 ('data-paperfile', file.filename),
                                 ('data-docid', str(file.id)),
                                 klass='btn-white btn-sm pdfbtn addmargin'):
                    deleted_line('i', '', klass='fa fa-folder')
                    deleted_line('span', ' {} '.format(
                        str(file.timestamp)[:19]))
            else:
                with files_tag('a',
                               ('data-paperid', str(file.paper_id)),
                               ('data-paperfile', file.filename),
                               ('data-docid', str(file.id)),
                               klass='btn-white btn-sm pdfbtn addmargin'):
                    files_line('i', '', klass='fa fa-folder')
                    files_line('span', ' {} '.format(
                        str(file.timestamp)[:19]))
        label = paper.label if paper.label else ''
        labels, tag, text, line = Doc().ttl()
        with tag('div', klass='input-group m-t-xs', style='margin-top: 0;'):
            labels.stag(
                'input',
                ('data-role', 'tagsinput'),
                style='float: left; width: 360px; padding: 5px, 10px; \
                position: static;',
                klass='form-control paper-label tagsinput',
                placeholder='Optional, separated by commas or semi-colons',
                value=label)
            with tag('span', klass="input-group-btn"):
                with tag('button',
                         ('data-paper-id', str(paper.id)),
                         klass="btn btn-primary save-labels"):
                    text('Save')
        questions, tag, text, line = Doc().ttl()
        for question_key, question in paper.custom_question_answer.iteritems():
            answer = question['answer']
            if isinstance(question['answer'], list):
                answer = ', '.join(answer)
            with tag('b'):
                text(question['desc'] + u':')
            text(answer)
            questions.stag('br')
            questions.stag('br')
        paper_json = {
            'id': paper.id,
            'title': paper.title,
            'author': indent(authors.getvalue()),
            'abstract': paper.abstract,
            'keywords': paper.keywords,
            'submission_time': str(paper.submitted_time),
            'submitted_by': indent(submitted_by.getvalue()),
            'reviews_button': indent(review_button.getvalue()),
            'files_button': indent(files.getvalue()),
            'deleted_files_button': indent(deleted.getvalue()),
            'label': {'value': indent(labels.getvalue()),
                      'options': {
                          'filterValue': label
                      }},
            'hide': indent(questions.getvalue()),
            'operation_button': '',
        }
        if tracks_list:
            paper_json['track'] = indent(tracks.getvalue())
        if status != 'Deleted':
            paper_json['operation_button'] = '<a class="btn-primary btn-sm" \
                href="' + url_for(
                    'paper.edit_paper_info', paper_id=paper.id) + \
                '">Edit</a>'
        if paper.submission_type:
            paper_json['submission_type'] = paper.submission_type
        else:
            paper_json['submission_type'] = ''
        submission_list.append(paper_json)
    return Response(dumps(submission_list), mimetype='application/json')
