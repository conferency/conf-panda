from . import api
from .. import db
from ..models import FavSession
from flask import jsonify, request
from flask.ext.login import current_user
from .authentication import auth
import random
from .errors import bad_request


@api.route('/fav_sessions', methods=['POST'])
@auth.login_required
def add_fav_session():
    new_fav_session = FavSession(user_id=current_user.id,
                                 session_id=request.json.get('session_id'))
    db.session.add(new_fav_session)
    try:
        db.session.commit()
        return 'Success', 201
    except:
        db.session.rollback()
        return bad_request('Cannot add new favorite session.')

@api.route('/fav_sessions', methods=['GET'])
@auth.login_required
def get_fav_session():
    sessions_json = {}
    for session in current_user.fav_sessions:
        conference = session.conference_schedule.conference
        sessions_json[session.id] = {
            'location': session.venue,
            'time': {
                'start': str(session.start_time)[:16],
                'end': str(session.end_time)[:16]
            },
            'title': session.title,
            'type': 'break' if session.type == 'regular' else session.type,
            'summary': session.description,
            'conference': conference.name,
            'timezone': conference.timezone
        }
        if session.type != 'regular':
            speakers = session.speakers.all()
            if speakers:
                sessions_json[session.id]['speakers'] = []
                for speaker in speakers:
                    speaker_json = speaker.conference_profile_for_api(
                        conference)
                    sessions_json[session.id]['speakers'].append({
                        'avatar': 'https://app.conferency.com' +
                        speaker_json['avatar'] + '?' + str(random.randint(0, 19)) if speaker_json['avatar'] else '',
                        'name': speaker_json['first_name'] + ' ' +
                        speaker_json['last_name'],
                        'organization': speaker_json['organization'],
                        'website': speaker_json['website'],
                        'summary': speaker_json['about_me'],
                        'email': speaker_json['email']
                    })
            moderators = session.moderators.all()
            if moderators:
                sessions_json[session.id]['chairs'] = []
                for moderator in moderators:
                    moderator_json = moderator.conference_profile_for_api(
                        conference)
                    sessions_json[session.id]['chairs'].append({
                        'avatar': 'https://app.conferency.com' +
                        moderator_json['avatar'] + '?' + str(random.randint(0, 19)) if moderator_json['avatar'] else '',
                        'name': moderator_json['first_name'] + ' ' +
                        moderator_json['last_name'],
                        'organization': moderator_json['organization'],
                        'website': moderator_json['website'],
                        'summary': moderator_json['about_me'],
                        'email': moderator_json['email']
                    })
            if session.type == 'paper':
                paper_sessions = session.paper_sessions.all()
                if paper_sessions:
                    sessions_json[session.id]['papers'] = []
                    for paper_session in paper_sessions:
                        paper_json = {
                            'abstract': paper_session.paper.abstract,
                            'title': paper_session.paper.title,
                            'authors': [{
                                'email': author.email,
                                'name': author.full_name,
                                'organization': author.organization,
                                'website': author.website
                            } for author in paper_session.paper.authors_list]
                        }
                        discussants = paper_session.discussants.all()
                        if discussants:
                            paper_json['discussants'] = []
                            for discussant in discussants:
                                discussant_json = discussant.conference_profile_for_api(conference)
                                # print discussant_json
                                paper_json['discussants'].append({
                                    'name': discussant_json['first_name'] + ' ' +
                                    discussant_json['last_name'],
                                    'email': discussant_json['email'],
                                    'organization': discussant_json['organization'],
                                    'website': discussant_json['website'],
                                    'summary': discussant_json['about_me'],
                                })
                        sessions_json[session.id]['papers'].append(paper_json)
    return jsonify(sessions_json)


@api.route('/fav_sessions', methods=['DELETE'])
@auth.login_required
def del_fav_session():
    fav_session = FavSession.query.filter_by(
        session_id=request.json.get('session_id'),
        user_id=current_user.id).first()
    if not fav_session:
        return bad_request('Cannot delete favorite session')
    db.session.delete(fav_session)
    try:
        db.session.commit()
        return 'Success', 200
    except:
        return bad_request('Cannot delete favorite session')
