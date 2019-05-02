# -*- coding: utf-8 -*-
"""Restful api for user."""

from flask import jsonify, request, current_app
from flask_login import current_user
from .decorators import admin_required
from sqlalchemy import or_
from . import api
from .. import db
from ..models import User, JoinTrack, Conference, Role, Track
from ..utils.email_operation import send_email
from .errors import conflict, forbidden, internal_error, bad_request
from .authentication import auth
import os
import base64


@api.route('/users/<int:user_id>')
@auth.login_required
def get_user(user_id):
    """Return user's info."""
    user = User.query.get_or_404(user_id)
    user_json = user.user_info_json()
    chair_role = Role.query.filter_by(name='Chair').first()
    user_json['is_chair'] = True if len(
        Conference.query.filter(
            Conference.id == Track.conference_id,
            Track.id == JoinTrack.track_id,
            JoinTrack.role_id == chair_role.id,
            JoinTrack.user_id == user_id
        ).all()
    ) else False
    return jsonify(user_json)
    # if user.id == current_user.id:
    #     return jsonify(user.to_json())
    # else:
    #     return jsonify(user.user_info_json())


@api.route('/conferences/<int:conference_id>/users/<int:user_id>')
@auth.login_required
def get_conference_user_profile(conference_id, user_id):
    """Return user's info."""
    conference = Conference.query.get_or_404(conference_id)
    user = User.query.get_or_404(user_id)
    profile_json = user.get_conference_profile(conference)
    if profile_json:
        return jsonify(profile_json)
    else:
        return forbidden('Not allowed')


@api.route('/conferences/<int:conference_id>/users/<int:user_id>',
           methods=['PUT'])
@auth.login_required
def update_conference_user_profile(conference_id, user_id):
    """Return user's info."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    if user.set_conference_profile(conference, request.json):
        return 'Success', 200
    else:
        return forbidden('Not allowed')


@api.route('/users', methods=['POST'])
def add_user():
    """Add new user."""
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    email = request.json.get('email')
    password = request.json.get('password')
    country = request.json.get('country')
    organization = request.json.get('organization')
    state = request.json.get('state')
    location = request.json.get('city')
    check_user = User.query.filter_by(email=email).first()
    if not check_user:
        user = User(first_name=first_name, last_name=last_name, email=email,
                    password=password, country=country, state=state,
                    organization=organization, location=location)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'email/confirm', user=user, token=token)
        return jsonify(user.to_json()), 201
    else:
        return conflict('Email address has been used')


@api.route('/app/users', methods=['POST'])
def app_add_user():
    """Add new user from app."""
    first_name = request.json.get('first_name')
    last_name = request.json.get('last_name')
    email = request.json.get('email')
    password = request.json.get('password')
    country = request.json.get('country')
    organization = request.json.get('organization')
    state = request.json.get('state')
    location = request.json.get('city')
    check_user = User.query.filter_by(email=email).first()
    if not check_user:
        user = User(first_name=first_name, last_name=last_name, email=email,
                    password=password, country=country, state=state,
                    organization=organization, location=location)
        try:
            db.session.add(user)
            db.session.commit()
            token = user.generate_confirmation_token()
            send_email(user.email, 'Confirm Your Account',
                       'email/confirm', user=user, token=token)
            return jsonify({
                'token': user.generate_auth_token(expiration=36000000),
                'expiration': 36000000,
                'user_id': user.id}), 201
        except:
            db.session.rollback()
            return bad_request('Check new user\'s inputs')
    else:
        return conflict('Email address has been used')


@api.route('/users/<int:user_id>', methods=['PUT'])
@auth.login_required
def update_user(user_id):
    """Update user's profile."""
    if current_user.id != user_id:
        return forbidden('Insufficient permissions')
    else:
        user = User.query.get(user_id)
        user.first_name = request.json.get('first_name', user.first_name)
        user.last_name = request.json.get('last_name', user.last_name)
        user.location = request.json.get('city', user.location)
        user.state = request.json.get('state', user.state)
        user.country = request.json.get('country', user.country)
        user.organization = request.json.get('organization', user.organization)
        # user.website
        # user.about_me
        try:
            db.session.add(user)
            db.session.commit()
            return 'Success', 200
        except Exception:
            return internal_error('Cannot store in the database')


@api.route('/users', methods=['GET'])
@auth.login_required
@admin_required
def list_user():
    """To list all users registered in the site excluding admins."""
    page = request.args.get('page', 1, type=int)
    name = request.args.get('name', '')
    users_per_page = current_app.config['CONF_FOLLOWERS_PER_PAGE'] or 20

    admin_list = [i.user_id for i in JoinTrack.query.filter_by(
        track_id=1, role_id=1)]
    if name == '':
        users_result = User.query.filter(
            User.id.notin_(admin_list)).filter_by(confirmed=True)
    else:
        try:
            first_name, last_name = name.split(' ')
        except ValueError:
            first_name = name
            last_name = name
        users_result = User.query.filter(or_(
                           User.first_name.contains(first_name),
                           User.last_name.contains(last_name))).filter(
                           User.id.notin_(admin_list)).filter_by(confirmed=True)
    pagination = users_result.paginate(page, per_page=users_per_page,
                                       error_out=False)
    users = pagination.items
    users_dict = [{'id': user.id, 'text': user.full_name} for user in users]
    return jsonify(users_dict)
# @api.route('/users/<int:id>/posts/')
# def get_user_posts(id):
#     user = User.query.get_or_404(id)
#     page = request.args.get('page', 1, type=int)
#     pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
#         page, per_page=current_app.config['CONF_POSTS_PER_PAGE'],
#         error_out=False)
#     posts = pagination.items
#     prev = None
#     if pagination.has_prev:
#         prev = url_for('api.get_posts', page=page - 1, _external=True)
#     next = None
#     if pagination.has_next:
#         next = url_for('api.get_posts', page=page + 1, _external=True)
#     return jsonify({
#         'posts': [post.to_json() for post in posts],
#         'prev': prev,
#         'next': next,
#         'count': pagination.total
#     })


# @api.route('/users/<int:id>/timeline/')
# def get_user_followed_posts(id):
#     user = User.query.get_or_404(id)
#     page = request.args.get('page', 1, type=int)
#     pagination = user.followed_posts.order_by(Post.timestamp.desc()).paginate(
#         page, per_page=current_app.config['CONF_POSTS_PER_PAGE'],
#         error_out=False)
#     posts = pagination.items
#     prev = None
#     if pagination.has_prev:
#         prev = url_for('api.get_posts', page=page - 1, _external=True)
#     next = None
#     if pagination.has_next:
#         next = url_for('api.get_posts', page=page + 1, _external=True)
#     return jsonify({
#         'posts': [post.to_json() for post in posts],
#         'prev': prev,
#         'next': next,
#         'count': pagination.total
#     })

@api.route('/users/search/', methods=['GET'])
@auth.login_required
def search_users():
    if request.args.get('first_name'):
        users = User.query.filter(
            User.full_name.contains(
                request.args['first_name'])).limit(20).all()
        search_result = {
            'suggestions': [
                {
                    'value': user.first_name,
                    'data': user.user_info_json()
                } for user in users]
            }
    elif request.args.get('last_name'):
        users = User.query.filter(
            User.last_name.contains(
                request.args['last_name'])).limit(20).all()
        search_result = {
            'suggestions': [
                {
                    'value': user.last_name,
                    'data': user.user_info_json()
                } for user in users]
            }
    elif request.args.get('email'):
        users = User.query.filter(
            User.email.contains(
                request.args['email'])).limit(20).all()
        search_result = {
            'suggestions': [
                {
                    'value': user.email,
                    'data': user.user_info_json()
                } for user in users]
            }
    else:
        return bad_request('Invalid parameter')
    return jsonify(search_result)


@api.route('/users/finishtour', methods=['POST'])
@auth.login_required
def tour_finished():
    """Update tour status."""
    data = request.json.get('status')
    if type(data) != bool:
        return forbidden('Wrong type')
    current_user.tour_finished = data
    db.session.add(current_user)
    db.session.commit()
    return 'Success', 201


@api.route('/conferences/<int:conference_id>/users/<int:user_id>/leave',
           methods=['POST'])
@auth.login_required
def leave_conference(conference_id, user_id):
    """User leaves a conference."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    user.leave_conference(conference)
    return 'Success', 201


@api.route('/users/<int:user_id>/change_avatar', methods=['PUT'])
@auth.login_required
def change_avatar(user_id):
    """Update user's avatar."""
    if not request.json or current_user.id != user_id:
        return forbidden('Cannot update avatar')
    else:
        data_url = request.json["dataUrl"].split(',')[-1]
        imgdata = base64.b64decode(data_url)
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'static', 'upload', 'avatar',
                            str(user_id) + '.png')
        with open(path, 'wb') as f:
            try:
                f.write(imgdata)
            except Exception:
                return forbidden('Cannot update avatar')
        user = User.query.get_or_404(user_id)
        user.avatar = '/' + os.path.join('static', 'upload',
                                         'avatar', str(user_id) + '.png')
        db.session.add(user)
        db.session.commit()
        return 'Success', 202


@api.route('/conferences/<int:conference_id>/users/<int:user_id>/img',
           methods=['PUT'])
@auth.login_required
def update_conference_user_profile_img(conference_id, user_id):
    """Return user's info."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    if not user.is_joined_conference(conference) or not request.json:
        return forbidden('Cannot update avatar')
    else:
        data_url = request.json["dataUrl"].split(',')[-1]
        imgdata = base64.b64decode(data_url)
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            'static', 'upload', 'avatar', str(user_id) +
                            '-' + str(conference_id) + '.png')
        with open(path, 'wb') as f:
            try:
                f.write(imgdata)
            except Exception:
                return forbidden('Cannot update avatar')
        jointrack = user.tracks.filter_by(
            track_id=conference.tracks.filter_by(
                default=True).first().id).first()
        jointrack.profile['avatar'] = '/' + os.path.join('static',
                                                         'upload',
                                                         'avatar',
                                                         str(user_id) + '-' +
                                                         str(conference_id) +
                                                         '.png')
        db.session.add(jointrack)
        db.session.commit()
        return 'Success', 202
