from flask import jsonify, request
from flask_login import current_user
from sqlalchemy import or_
from .. import db
from ..models import Session, Conference, User, PaperSession, Paper, \
    ConferenceSchedule, Author
from . import api
import datetime
from .errors import not_found, forbidden
import random
from .authentication import auth


@api.route('/conferences/<int:conference_id>/sessions/', methods=['POST'])
@auth.login_required
def new_session(conference_id):
    """Add new session."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    new_session = Session(
        conference_schedule_id=conference.conference_schedule.id,
        type=request.json.get('type'),
        title=request.json.get('title'),
        venue=request.json.get('venue'),
        description=request.json.get('description'),
        start_time=datetime.datetime.strptime(
            request.json['start_time'], '%Y-%m-%d %H:%M'),
        end_time=datetime.datetime.strptime(
            request.json['end_time'], '%Y-%m-%d %H:%M'))
    db.session.add(new_session)
    db.session.commit()
    if request.json.get('speakers'):
        for user_id in request.json.get('speakers'):
            new_session.speakers.append(User.query.get_or_404(user_id))
    if request.json.get('moderators'):
        for user_id in request.json.get('moderators'):
            new_session.moderators.append(User.query.get_or_404(user_id))
    if request.json.get('papers'):
        for paper_info in request.json.get('papers'):
            paper_session = PaperSession(
                paper_id=Paper.query.get_or_404(
                    paper_info.get('paper_id')).id,
                session_id=new_session.id)
            if paper_info['discussants']:
                for user_id in paper_info['discussants']:
                    paper_session.discussants.append(
                        User.query.get_or_404(user_id))
            db.session.add(paper_session)
            new_session.paper_sessions.append(paper_session)
    db.session.add(new_session)
    db.session.commit()
    return jsonify(new_session.to_json()), 201


@api.route('/conferences/<int:conference_id>/sessions/',
           methods=['PUT'])
@auth.login_required
def edit_session(conference_id):
    """Update session."""
    session_data = request.json['data']
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    session = conference.conference_schedule.sessions.filter_by(
        id=session_data['session_id']).first()
    if session:
        session.start_time = datetime.datetime.strptime(
            session_data['start_time'], '%Y-%m-%d %H:%M')
        session.end_time = datetime.datetime.strptime(
            session_data['end_time'], '%Y-%m-%d %H:%M')
        if request.json['operation'] == 'update_session':
            session.title = session_data['title']
            session.venue = session_data['venue']
            session.type = session_data['type']
            session.description = session_data['description']
            if session_data['type'] != 'regular':
                session.speakers = []
                if session_data.get('speakers'):
                    for user_id in session_data['speakers']:
                        session.speakers.append(User.query.get_or_404(user_id))
                session.moderators = []
                if session_data.get('moderators'):
                    for user_id in session_data['moderators']:
                        session.moderators.append(
                            User.query.get_or_404(user_id))
                if session_data['type'] == 'paper':
                    if session_data['papers']:
                        session.paper_sessions = []
                        for paper_info in session_data['papers']:
                            paper_session = PaperSession(
                                paper_id=Paper.query.get_or_404(
                                    paper_info.get('paper_id')).id,
                                session_id=session.id)
                            if paper_info.get('discussants'):
                                for user_id in paper_info['discussants']:
                                    paper_session.discussants.append(
                                        User.query.get_or_404(user_id))
                            db.session.add(paper_session)
                            session.paper_sessions.append(paper_session)
    db.session.add(session)
    db.session.commit()
    return jsonify(session.to_json()), 200


@api.route('/conferences/<int:conference_id>/sessions/',
           methods=['DELETE'])
@auth.login_required
def delete_session(conference_id):
    """Update session."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    session = conference.conference_schedule.sessions.filter_by(
        id=request.json['session_id']).first()
    session.status = 'Deleted'
    if session:
        db.session.add(session)
        db.session.commit()
        return 'Success', 200
    else:
        not_found('No session was found')

@api.route('/sessions/<keyword>')
def search_session(keyword):
    """Search for sessions"""
    sessions = Session.query.filter(
        Session.conference_schedule_id == ConferenceSchedule.id,
        ConferenceSchedule.publish == True,
    ).filter(
        or_(Session.venue.contains(keyword),
            Session.title.contains(keyword),
            Session.description.contains(keyword),
            Session.speakers.any(User.full_name.contains(keyword)),
            Session.moderators.any(User.full_name.contains(keyword)),
            Session.papers.any(Paper.title.contains(keyword)),
            Session.papers.any(Paper.keywords.contains(keyword)),
            Session.papers.any(Paper.abstract.contains(keyword)),
            Session.papers.any(Paper.authors_list.any(Author.full_name.contains(keyword))))
    ).all()
    sessions_json = {}
    for session in sessions:
        sessions_json[session.id] = {
            'location': session.venue,
            'time': {
                'start': str(session.start_time)[:16],
                'end': str(session.end_time)[:16]
            },
            'title': session.title,
            'type': 'break' if session.type == 'regular' else session.type,
            'summary': session.description
        }
        conference = session.conference_schedule.conference
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
