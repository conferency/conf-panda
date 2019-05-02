# -*- coding: utf-8 -*-
"""Restful api for authentication."""

from flask import jsonify, request, json, g
from flask.ext.httpauth import HTTPBasicAuth
from ..models import User
from . import api
from .errors import unauthorized, forbidden, bad_request
from flask.ext.login import current_user, login_user
import re
from ..utils.email_operation import send_email

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    """Verify token or password."""
    # for website
    if current_user.is_authenticated:
        return True
    user = User.verify_auth_token(email_or_token)
    if not user:
        # try to authenticate with username/password
        user = User.query.filter_by(email=email_or_token).first()
        if not user or not user.verify_password(password):
            return False
    login_user(user)
    return True
    # if current_user.is_anonymous:
    #     # first try to authenticate by token
    #     user = User.verify_auth_token(email_or_token)
    #     if not user:
    #         # try to authenticate with username/password
    #         user = User.query.filter_by(email=email_or_token).first()
    #         if not user or not user.verify_password(password):
    #             return False
    #     login_user(user)
    #     return True
    # else:
    #     return True
    # if email_or_token == '':
    #     g.current_user = AnonymousUser()
    #     return False
    # if password == '':
    #     g.current_user = User.verify_auth_token(email_or_token)
    #     g.token_used = True
    #     return g.current_user is not None
    # user = User.query.filter_by(email=email_or_token).first()
    # if not user:
    #     return False
    # g.current_user = user
    # g.token_used = False
    # return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
def before_request():
    # pass
    # if current_user.is_anonymous:
    #     g.current_user = AnonymousUser()
    # if not current_user.is_authenticated:
    #     print 'Invalid credentials'
    #     return unauthorized('Invalid credentials')
    # else:
    # if
    g.current_user = current_user
    # print 'before request'
    # if not g.current_user.is_anonymous and \
    #         not g.current_user.confirmed:
    #     return forbidden('Unconfirmed account')


@api.route('/token')
@auth.login_required
def get_token():
    if current_user.is_anonymous:
        return unauthorized('Invalid credentials')
    return jsonify({
        'token': current_user.generate_auth_token(expiration=36000000),
        'expiration': 36000000,
        'user_id': current_user.id})


@api.route('/check_email', methods=['POST'])
def check_email():
    # Regex to check email
    email_regex = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
    # Judge different content types
    if request.headers['Content-Type'] == 'text/plain':
        if not request.data:
            return forbidden("Not allowed. Empty request.")
    elif request.headers['Content-Type'] == 'application/json':
        if not request.json:
            return forbidden("Not allowed. Empty json request.")
    else:
        return forbidden('Not allowed for this content type:' +
                         request.headers['Content-Type'])
    # Try to catch required data
    try:
        request_json = request.json if request.json else request.data if request.data else request.form
    except Exception:
        return forbidden("Error parsing data:" + request.data)

    # If no email in request, raise an error.
    if not request_json.get('email', ""):
        return forbidden("Empty request" + json.dumps(request_json))

    email = str(request_json['email']).strip()
    return_msg = {'email': email, 'request': json.dumps(
        request_json)}  # return msg structure

    if not re.compile(email_regex).match(email):
        return_msg['code'] = 409
        return_msg['error'] = 'invalid'
        return_msg['message'] = 'Invalid email address.'
    elif User.query.filter_by(email=email).first():
        return_msg['code'] = 409
        return_msg['error'] = 'registered'
        return_msg['message'] = 'Email already registered.'
    else:
        return_msg['code'] = 200
        return_msg['message'] = ''
    return jsonify(return_msg)


# @api.route('/login', methods=['POST'])
# def login():
#     email = request.json.get(email)
#     password = request.json.get(password)


@api.route('/test')
@auth.login_required
def api_test():
    """Test authentication."""
    return jsonify({
        'email': current_user.email,
        'name': current_user.full_name
    })


@api.route('/auth/reset_password', methods=['POST'])
def reset_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if user:
        token = user.generate_reset_token()
        send_email(user.email, 'Reset Your Password',
                   'email/reset_password',
                   user=user, token=token,
                   next=request.args.get('next'))
        return 'Success', 201
    else:
        return bad_request('email no found')
