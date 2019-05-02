# -*- coding: utf-8 -*-
"""Restful api for custom question."""

from collections import OrderedDict

from flask import request, jsonify
from flask_login import current_user

from . import api
from .authentication import auth
from .errors import bad_request, forbidden
from .. import db
from ..models import Conference
from ..utils.macros import generate_uuid


def validate_request_json(request_json):
    for question in request_json:
        try:
            ques_type = int(question['ques_type'])
        except:
            raise Exception('Invalid Question Type')

        if ques_type < 2:
            if len(question.get('options', [])) == 0:
                raise Exception('Missing options')
            if ques_type == 0:
                if len(question['options']) == 1:
                    raise Exception('Options less than two')

@api.route('/configurations/<int:conference_id>/submission_question',
           methods=['PUT'])
@auth.login_required
def update_submission_question(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if not request.json:
        return bad_request('Empty question list')
    else:
        submission_questions = OrderedDict()
        if request.json[0]:
            try:
                validate_request_json(request.json)
            except Exception as e:
                return bad_request(e.message)

            for question in request.json[::-1]:
                question_json = {'ques_type': int(question['ques_type']),
                                 'desc': question['desc'].encode('utf-8'),
                                 'require': question['require'],
                                 'include': question['include'],
                                 'id': question['uuid'] if question.get(
                                 'uuid', False) and len(question['uuid']) >= 3
                                 else generate_uuid(),
                                 'numid': question['numid']}
                if question_json['ques_type'] < 2:
                    question_json['options'] = [
                        option.encode('utf-8') for option in question[
                            'options']]
                submission_questions[question_json['id']] = question_json
        # curr_questions = conference.review_questions
        conference.submission_questions = submission_questions
        # conference.review_deadline = datetime.strptime(
        #     request.json['review_acceptance_deadline'], "%Y-%m-%d").date()
        db.session.add(conference)
        db.session.commit()
        return jsonify(dict(enumerate(submission_questions))), 200


@api.route('/configurations/<int:conference_id>/review_question',
           methods=['PUT'])
@auth.login_required
def update_review_question(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if not request.json:
        return bad_request('Empty question list')
    else:
        review_questions = OrderedDict()
        if request.json[0]:
            try:
                validate_request_json(request.json)
            except Exception as e:
                return bad_request(e.message)

            for question in request.json[::-1]:
                question_json = {'ques_type': int(question['ques_type']),
                                 'desc': question['desc'].encode('utf-8'),
                                 'require': question['require'],
                                 'include': question['include'],
                                 'id': question['uuid'] if question.get(
                                 'uuid', False) and len(question['uuid']) >= 3
                                 else generate_uuid(),
                                 'numid': question['numid']}
                if question_json['ques_type'] < 2:
                    question_json['options'] = [
                        option.encode('utf-8') for option in question[
                            'options']]
                review_questions[question_json['id']] = question_json
        # curr_questions = conference.review_questions
        conference.review_questions = review_questions
        # conference.review_deadline = datetime.strptime(
        #     request.json['review_acceptance_deadline'], "%Y-%m-%d").date()
        db.session.add(conference)
        db.session.commit()
        return jsonify(dict(enumerate(review_questions))), 200


@api.route('/configurations/<int:conference_id>/registration_form_question',
           methods=['PUT'])
@auth.login_required
def update_registration_question(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if not request.json:
        return bad_request('Empty question list')
    else:
        registration_questions = OrderedDict()
        # curr_questions = conference.registration.private_question
        # if no of customized question > 0
        if request.json[0]:
            try:
                validate_request_json(request.json)
            except Exception as e:
                return bad_request(e.message)

            for question in request.json[::-1]:
                question_json = {'ques_type': int(question['ques_type']),
                                 'desc': question['desc'].encode('utf-8'),
                                 'require': True,
                                 'include': True,
                                 'id': question['uuid'] if question.get(
                                    'uuid', False) and
                                 len(question['uuid']) >= 3
                                 else generate_uuid(),
                                 'numid': question['numid']}
                if question_json['ques_type'] < 2:
                    question_json['options'] = [
                        option.encode('utf-8') for option in question[
                            'options']]
                registration_questions[question_json['id']] = question_json
        conference.registration.private_question = registration_questions
        db.session.add(conference)
        db.session.commit()
        return jsonify(dict(enumerate(registration_questions))), 200


@api.route(
    '/configurations/<int:conference_id>/delete_registration_form_question',
    methods=['DELETE'])
@auth.login_required
def delete_registration_question(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if not request.json:
        return bad_request('Empty question list')
    else:
        print request.json
        curr_questions = conference.registration.private_question
        id = str(request.json['numid'])
        for uuid, question in curr_questions.items():
            if question['numid'] == id:
                curr_questions.pop(str(uuid))
        questions = OrderedDict()
        id = 0
        for uuid, question in curr_questions.items():
            question['numid'] = str(id)
            questions[uuid] = question
            id = id + 1
        conference.registration.private_question = questions
        db.session.add(conference)
        db.session.commit()
        return jsonify(dict(enumerate(questions))), 200


@api.route('/configurations/<int:conference_id>/delete_review_form_question',
           methods=['DELETE'])
@auth.login_required
def delete_review_question(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if not request.json:
        return bad_request('Empty question list')
    else:
        curr_questions = conference.review_questions
        id = str(request.json['numid'])
        for uuid, question in curr_questions.items():
            if question['numid'] == id:
                curr_questions.pop(str(uuid))
        questions = OrderedDict()
        id = 0
        for uuid, question in curr_questions.items():
            question['numid'] = str(id)
            questions[uuid] = question
            id = id + 1
        conference.review_questions = questions
        db.session.add(conference)
        db.session.commit()
        return jsonify(dict(enumerate(questions))), 200
