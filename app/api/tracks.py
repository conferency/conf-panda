from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import Track, Conference, User, Permission
from . import api
from .errors import forbidden, not_acceptable, bad_request
from .authentication import auth


@api.route('/tracks')
def get_all_tracks():
    tracks = Track.query.all()
    return jsonify({'tracks': [track.to_json() for track in tracks]})

# #this information has moved to /api/conferences/<int:conference_id>
# @api.route('/tracks/<int:track_id>/track_members')
# def get_track_members(track_id):
#     track = Track.query.get_or_404(track_id)
#     members=[]
#     track_chairs=[]
#     json_comment={}
#     for member in track.members:
#         members.append(member.member)
#         user=member.member
#         if user.is_track_chair(track):
#             track_chairs.append(user)
#     json_comment['track_chairs']=[ {'id':track_chair.id, 'name': track_chair.first_name + ' ' + track_chair.last_name} for track_chair in track_chairs]
#     json_comment['members']=[{'id':member.id, 'name': member.first_name + ' ' + member.last_name} for member in members]
#     return jsonify(json_comment)


@api.route('/conferences/<int:id>/tracks')
def get_tracks(id):
    conference = Conference.query.get_or_404(id)
    tracks = conference.tracks.all()
    return jsonify({'tracks': [track.to_json() for track in tracks]})


@api.route('/conferences/<int:id>/tracks', methods=['POST'])
@auth.login_required
def add_tracks(id):
    conference = Conference.query.get_or_404(id)
    track = Track(name=request.json['track_name'], conference_id=conference.id)
    db.session.add(track)
    db.session.commit()
    return jsonify({'id': track.id}), 201


@api.route('/tracks', methods=['DELETE'])
@auth.login_required
def delete_tracks():
    # get the ids * security problem
    track = Track.query.get_or_404(request.json['track_id'])
    if not current_user.is_chair(track.conference):
        return forbidden('Not allowed')
    track.status = False
    db.session.add(track)
    db.session.commit()
    return 'Success', 200


@api.route('/conferences/<int:conference_id>/update_track_name', methods=['PUT'])
@auth.login_required
def update_track_name(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    track = conference.tracks.filter_by(id=request.json['track_id']).first()
    if not track:
        return not_acceptable('Wrong Value')
    track.name = request.json['new_track_name']
    db.session.add(track)
    db.session.commit()
    return 'Success', 200


@api.route('/conferences/<int:conference_id>/update_track_relation', methods=['PUT'])
@auth.login_required
def update_track_relation(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    track = conference.tracks.filter_by(id=request.json['track_id']).first()
    if not track:
        return not_acceptable('Wrong Value')
    track.parent_track_id = request.json['parent_track_id']
    db.session.add(track)
    db.session.commit()
    return 'Success', 200


# @api.route('/conferences/<int:id>/tracks', methods=['PUT'])
# @auth.login_required
# def update_tracks(id):
#     conference = Conference.query.get_or_404(id)
#     if not current_user.is_chair(conference):
#         return forbidden('Not allowed')
#     for track_dict in request.json['change_tracks']:
#         track = Track.query.get(track_dict['id'])
#         track.name = track_dict['name']
#         db.session.add(track)
#     # for name in request.json['add_tracks']:
#     # 	# print name
#     # 	track = Track(name=name, conference_id=conference.id)
#     # 	db.session.add(track)
#     db.session.commit()
#     return 'Success', 200


# For a conference, get a user's tracks.
@api.route('/conferences/<int:id>/users/<int:user_id>/tracks')
@auth.login_required
def get_user_tracks(id, user_id):
    conference = Conference.query.get_or_404(id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    user = User.query.get_or_404(user_id)
    tracks = conference.tracks.all()
    return jsonify(
        {
            'tracks': [
                track.to_json() for track in tracks if user.is_track_chair(track)]})


@api.route(
    '/conferences/<int:conference_id>/track/<int:track_id>/track_setting',
    methods=['PUT'])
@auth.login_required
def update_track_setting(conference_id, track_id):
    # print request.json
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.can(Permission.MANAGE_REVIEW, conference):
        return forbidden('Not allowed')
    track = conference.tracks.filter(Track.id == track_id,
                                     Track.status == True).first()
    # update configuration
    if track:
        for key, value in request.json['setting'].iteritems():
            track.configuration[key] = value
        db.session.add(track)
        db.session.commit()
        return 'Success', 200
    else:
        return bad_request('Not allowed')


@api.route(
    '/conferences/<int:conference_id>/track/<int:track_id>/track_setting/<type>',
    methods=['GET'])
@auth.login_required
def get_track_setting(conference_id, track_id, type):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.can(Permission.MANAGE_REVIEW, conference):
        return forbidden('Not allowed')
    track = conference.tracks.filter(Track.id == track_id,
                                     Track.status == True).first()
    if track:
        if (type == 'submission' and track.configuration.get(
            'allow_submission_config', False)) or \
            (type == 'review' and track.configuration.get(
             'allow_review_config', False)):
            return jsonify(track.configuration)
        else:
            return jsonify(conference.configuration)
    else:
        return bad_request('Not allowed')
