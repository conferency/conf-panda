# -*- coding: utf-8 -*-
"""Apis for email preview."""


from flask import request
from flask_login import current_user
from ..models import User, Author
from . import api
from .errors import bad_request, forbidden
from ..utils.email_operation import send_email
from .authentication import auth


def validate_json(json):
    """Validate request json."""
    for k, v in json.iteritems():
        if not v:
            return False
    return True


@api.route('/notifications/send_testing_email', methods=['POST'])
@auth.login_required
def send_testing_email():
    """Send testing email function.

    request.json:
        subject, content, email, operation, receiver
    """
    if not current_user.is_chair(current_user.curr_conf):
        return forbidden('Not allowed')
    if (not validate_json(request.json)) or current_user.curr_conf_id == 1:
        return bad_request('Request is invalid.')
    if request.json['operation'] == 'author':
        user = Author.query.get(request.json['receiver_id'])
    else:
        user = User.query.get(request.json['receiver_id'])
    if send_email(request.json['email'], request.json['subject'],
                  'email/notification_members',
                  reply_to=current_user.curr_conf.contact_email,
                  content=request.json['content'],
                  conference=current_user.curr_conf, user=user):
        return 'Success', 200
    else:
        return bad_request('Email has not been sent Successfully.')
