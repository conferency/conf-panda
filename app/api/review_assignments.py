# -*- coding: utf-8 -*-
"""Restful api for review Assignments."""

from flask import request, jsonify
from . import api
from .. import db
from ..models import Paper, Permission, User, PaperStatus, paper_author,\
    DelegateReview
from flask_login import current_user
from .authentication import auth
from .errors import forbidden, bad_request


@api.route('/papers/<int:paper_id>/reviewers/', methods=['POST'])
@auth.login_required
def add_review_assginment(paper_id):
    """Add a reviewer for a paper."""
    paper = Paper.query.get_or_404(paper_id)
    if not current_user.can(Permission.MANAGE_REVIEW, paper.conference):
        return forbidden('Not allowed')
    reviewer = User.query.get_or_404(request.json.get('user_id'))
    paper.reviewers.append(reviewer)
    paper.status = PaperStatus.UNDER_REVIEW
    db.session.add(paper)
    try:
        db.session.commit()
        return jsonify({
            'user_id': reviewer.id,
            'if_has_review': paper.if_has_review(reviewer)
        }), 201
    except Exception:
        db.session.rollback()
        return bad_request('Bad request')


@api.route('/papers/<int:paper_id>/reviewers/<user_id>', methods=['DELETE'])
@auth.login_required
def remove_review_assginment(paper_id, user_id):
    """Add a reviewer for a paper."""
    paper = Paper.query.get_or_404(paper_id)
    if not current_user.can(Permission.MANAGE_REVIEW, paper.conference):
        return forbidden('Not allowed')
    reviewer = User.query.get_or_404(user_id)
    paper.reviewers.remove(reviewer)
    db.session.add(paper)
    try:
        db.session.commit()
        return 'Success', 201
    except Exception:
        db.session.rollback()
        return bad_request('Bad request')


@api.route('/papers/<int:paper_id>/reviewers/<user_id>', methods=['GET'])
@auth.login_required
def precheck_review_assignment(paper_id, user_id):
    """Pre-check review assignment."""
    paper = Paper.query.get_or_404(paper_id)
    if not current_user.can(Permission.MANAGE_REVIEW, paper.conference):
        return forbidden('Not allowed')
    reviewer = User.query.get_or_404(user_id)
    authors = paper.authors.all()
    if reviewer in authors:
        return bad_request('Author of this paper')
    reviewers = paper.reviewers.all()
    if reviewer in reviewers:
        return bad_request('Reviewer of this paper')
    # if this usr has delegated to sub reviewers
    delegation = DelegateReview.query.filter(
        DelegateReview.delegator_id == reviewer.id,
        DelegateReview.paper_id == paper_id,
        DelegateReview.status == 'Accepted').first()
    if delegation:
        return bad_request('Delegator of this paper')
    errors = []
    try:
        max_reviewer = int(
            paper.conference.configuration.get('max_reviewer', 0))
    except Exception:
        max_reviewer = 0
    if max_reviewer and max_reviewer <= len(reviewers):
        errors.append('Max reviewers limit (' + str(max_reviewer) + ')')
    try:
        max_paper = int(paper.conference.configuration.get('max_paper', 0))
    except Exception:
        max_paper = 0
    if max_paper and max_paper <= len(
            reviewer.review_assignment_conference(paper.conference)):
        errors.append(
            'Max review assignment limit (' + str(max_paper) + ')')
    if reviewer.organization in [author.organization for author in authors]:
        errors.append('Same organization')
    if paper.get_bid(reviewer) == 2:
        errors.append('Prefer not to review this paper')
    paper_ids = []
    for author in authors:
        paper_ids += [
            _paper.id for _paper in author.papers.filter(
                Paper.status != PaperStatus.DELETED).all()]
    if db.session.query(paper_author).filter(
            paper_author.c.user_id == user_id,
            paper_author.c.user_id.in_(paper_ids)).all():
            errors.append('Cooperated with authors')
    if errors:
        return bad_request(', '.join(errors))
    return 'Success', 200
