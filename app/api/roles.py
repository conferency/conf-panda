from flask import g
from ..models import Track, Conference, User, Role, Permission
from . import api
from .errors import bad_request, forbidden
from flask_login import current_user
from .authentication import auth


# change a user's role in conference (stored in default track)
@api.route(
    '/conferences/<int:conf_id>/users/<int:user_id>/roles/<string:role_name>')
@auth.login_required
def change_conference_role(conf_id, user_id, role_name):
    if role_name == 'PC':
        role_name = 'Program Committee'
    # elif role_name == 'TC':
    #     role_name = 'Track Chair'
    conference = Conference.query.get_or_404(conf_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    role = Role.query.filter_by(name=role_name).first()
    if user == current_user:
        # cannot change its own role
        return bad_request('')
    if role:
        if user.is_chair(conference) and len(conference.chairs) == 1 and role_name != "Chair":
            return 'The conference must have at least one chair', 400
        else:
            user.update_conference_role(conference, role)
            return 'Success', 200
    else:
        return bad_request('Cannot find the role')


# change a user's role in a track
@api.route('/tracks/<int:track_id>/users/<int:user_id>/roles/<string:role_name>',
           methods=['PUT'])
@auth.login_required
def change_track_role(track_id, user_id, role_name):
    """Change user's role in a track."""
    track = Track.query.get_or_404(track_id)
    if not current_user.can((Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION), track.conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    if user == current_user:
        # cannot change its own role
        return bad_request('Cannot change your own role')
    if role_name == 'None':
        user.leave_track(track)
        return 'Success', 200
    role = Role.query.filter_by(name=role_name).first()
    if user and role:
        user.join_track(track, role)
        return 'Success', 200
    else:
        return bad_request('Cannot find the role')


# let a user leave the track
@api.route('/tracks/<int:track_id>/users/<int:user_id>/leave',
           methods=['DELETE'])
@auth.login_required
def leave_track(track_id, user_id):
    track = Track.query.get_or_404(track_id)
    if not current_user.can((Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION), track.conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    user.leave_track(track)
    return 'Success', 200
