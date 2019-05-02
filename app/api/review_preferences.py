# -*- coding: utf-8 -*-
"""Restful api for review preference."""


from flask import request
from .. import db
from ..models import ReviewPreference
from . import api
from .errors import internal_error, forbidden
from .authentication import auth
from flask.ext.login import current_user


@api.route(
    '/conferences/<int:conference_id>/review_preference/<int:reviewer_id>',
    methods=['PUT'])
@auth.login_required
def update_review_preference(conference_id, reviewer_id):
    if current_user.id == reviewer_id:
        review_preference = ReviewPreference.query.filter_by(
            reviewer_id=reviewer_id, conference_id=conference_id).first()
        if 'assigned_reviews_max' in request.json:
            review_preference.assigned_reviews_max = request.json[
                'assigned_reviews_max']
        elif 'preferred_keywords' in request.json:
            review_preference.preferred_keywords = request.json[
                'preferred_keywords']
        elif 'rejected_keywords' in request.json:
            review_preference.rejected_keywords = request.json[
                'rejected_keywords']
        else:
            pass
        try:
            db.session.add(review_preference)
            db.session.commit()
            return 'Success', 200
        except Exception:
            db.session.rollback()
            internal_error('Database error')
    else:
        forbidden('Insufficient permission')
