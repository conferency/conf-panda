# -*- coding: utf-8 -*-
"""Apis for email preview."""


from flask import request, jsonify
from flask_login import current_user
from ..models import User, Author
from . import api
from .errors import bad_request, forbidden
from ..utils.template_convert import template_convert
from .authentication import auth


def validate_json(json):
    """Validate request json."""
    for k, v in json.iteritems():
        if not v:
            return False
    return True


@api.route('/notifications/email_preview', methods=['POST'])
@auth.login_required
def email_preview():
    """Email preview function.

    request.json:
        operation, content, receiver_id
    """
    if not current_user.is_chair(current_user.curr_conf):
        return forbidden('Not allowed')
    if not validate_json(request.json):
        return bad_request('Request is invalid.')
    if request.json['operation'] == 'author':
        user = Author.query.get(request.json['receiver_id'])
    else:
        user = User.query.get(request.json['receiver_id'])
    if user:
        return jsonify({
            'content': template_convert(
                request.json['content'],
                request.json['operation'],
                user,
                send_to=request.json.get('type'))})
    else:
        return bad_request('Cannot find receiver.')
