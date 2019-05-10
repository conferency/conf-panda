# -*- coding: utf-8 -*-
"""Restful api for conference."""

import json
import re
import sys
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
from random import shuffle, choice
try:
    import cStringIO as StringIO
except ImportError:
    from io import StringIO
import xlsxwriter
import requests
from flask import jsonify, request, current_app, url_for, abort, Response
from flask_login import current_user

from . import api
from .authentication import auth
from .decorators import admin_required, chair_required
from .errors import forbidden, not_found, bad_request, internal_error
from .. import db
from ..models import Conference, Paper, Permission, User, JoinTrack, Track, \
    Role, Review, PaperStatus, paper_reviewer
from ..utils.email_operation import send_email
from ..utils.website import wordpress_update_contact


# return all conferences
@api.route('/conferences')
@auth.login_required
def get_conferences():
    conferences = Conference.query.all()
    return jsonify({'conferences':
                    [conference.to_json() for conference in conferences]})


# return queried conference
@api.route('/conferences/<int:id>')
@auth.login_required
def get_conference(id):
    conference = Conference.query.get_or_404(id)
    return jsonify(conference.to_json())


@api.route('/conferences/<int:conference_id>/members')
@auth.login_required
def get_conference_member(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.can(
            (Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION),
            conference):
        return forbidden('Not allowed')
    if current_user.curr_conf_id == 1:
        forbidden('Not allowed')
    name = request.args.get('name', '')
    # member_list = [
    #     {
    #         'text': member.full_name + ' <' + member.email + '>',
    #         'id': member.id
    #     } for member in conference.members]
    if name == '':
        # return empty member list
        users_result = []
    else:
        users_result = []
        members = User.query.filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id == conference.tracks.filter_by(
                default=True).first().id,
            User.full_name.contains(name)).all()
        for member in members:
            users_result.append({
                'text': member.full_name + ' <' + member.email + '>',
                'id': member.id
            })
        # for member in member_list:
        #     if member['text'].lower().find(name.lower()) != -1:
        #         users_result.append(member)
    return jsonify({'members': users_result})


# return conference papers
@api.route('/conferences/<int:conference_id>/papers/')
@auth.login_required
def get_conference_paper(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if current_user.curr_conf_id == 1 or not current_user.is_chair(conference):
        return forbidden('Not allowed')
    title = request.args.get('name', '')
    if title:
        papers = conference.get_papers.filter(
            Paper.title.contains(title)).all()
        paper_list = [
            {'text': paper.title, 'id': paper.id} for paper in papers]
    else:
        paper_list = []
    return jsonify({'papers': paper_list})


# update specific conference
@api.route('/conferences/<int:id>', methods=['PUT'])
@auth.login_required
def update_conference(id):
    conference = Conference.query.get_or_404(id)
    if not request.json:
        return 'Bad request', 400
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    else:
        update_contact = False
        if request.json['contact_email'] != conference.contact_email and \
                conference.configuration.get('wordpress_activation'):
            update_contact = True

        subjects = ';'.join(request.json['subjects'])
        website = request.json['website'].replace(
            'http://', '').replace('https://', '')
        conference.name = request.json['name']
        conference.short_name = request.json['short_name']
        conference.website = website
        conference.contact_email = request.json['contact_email']
        conference.contact_phone = request.json['contact_phone']
        conference.address = request.json['address']
        conference.city = request.json['city']
        conference.state = request.json['state']
        conference.country = request.json['country']
        conference.start_date = datetime.strptime(
            request.json['start_date'], "%Y-%m-%d").date()
        conference.end_date = datetime.strptime(
            request.json['end_date'], "%Y-%m-%d").date()
        conference.timezone = request.json['timezone']
        conference.info = request.json['info']
        conference.subjects = subjects
        conference.tags = request.json['tags']
        # conference.featured = request.json['featured']
        db.session.add(conference)
        db.session.commit()

        if update_contact:
            wordpress_update_contact(conference)

        return 'Success', 200


@api.route('/conferences/<int:conference_id>/review_config', methods=['PUT'])
@auth.login_required
def update_conference_review_config(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if request.json.get('questions'):
        review_questions = OrderedDict()
        for question in request.json['questions']:
            question_json = {'ques_type': int(question['ques_type']),
                             'desc': str(question['desc']),
                             'require': question['require'],
                             'include': question['include']}
            if question_json['ques_type'] < 2:
                question_json['options'] = [
                    str(option) for option in question['options']]
            review_questions[question['id']] = question_json
        conference.review_questions = review_questions
    # if request.json.get('review_acceptance_deadline') and request.json['review_acceptance_deadline'].strip() != '':
    #     conference.review_deadline = datetime.strptime(
    # request.json['review_acceptance_deadline'].strip(), '%Y-%m-%d').date()
    if request.json.get('setting'):
        configuration = deepcopy(conference.configuration)
        for key, value in request.json['setting'].iteritems():
            configuration[key] = value
        conference.configuration = configuration
    try:
        db.session.add(conference)
        db.session.commit()
        return 'Success', 200
    except Exception:
        return 'Content not acceptable', 406


@api.route('/conferences/<int:conference_id>/submission_config',
           methods=['PUT'])
@auth.login_required
def update_conference_submission_config(conference_id):
    """Update submission configuration."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if request.json.get('questions'):
        submission_questions = OrderedDict()
        for question in request.json['questions']:
            question_json = {'ques_type': int(question['ques_type']),
                             'desc': str(question['desc']),
                             'require': question['require'],
                             'include': question['include']}
            if question_json['ques_type'] < 2:
                question_json['options'] = [
                    str(option) for option in question['options']]
            submission_questions[question['id']] = question_json
        conference.submission_questions = submission_questions
    if request.json.get('setting'):
        configuration = deepcopy(conference.configuration)
        for key, value in request.json['setting'].iteritems():
            if key == 'submission_types':
                value = re.sub(r',(\s+)', ',', value)
            configuration[key] = value
        conference.configuration = configuration
    try:
        db.session.add(conference)
        db.session.commit()
        return 'Success', 200
    except Exception:
        return 'Content not acceptable', 406


@api.route('/conferences/<int:conference_id>/config',
           methods=['PUT'])
@auth.login_required
def update_conference_config(conference_id):
    """Update conference configuration."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    if request.json.get('setting'):
        configuration = deepcopy(conference.configuration)
        for key, value in request.json['setting'].iteritems():
            configuration[key] = value
        conference.configuration = configuration
    try:
        db.session.add(conference)
        db.session.commit()
        return 'Success', 200
    except Exception:
        return 'Content not acceptable', 406


@api.route('/conferences/check_short_name', methods=['POST'])
def check_short_name():
    patrn = r"^[a-zA-Z]+\d{4}$"
    patrn_space = r"^[a-zA-Z]*\s+[a-zA-Z]*$"
    patrn_letter_number = "^[a-zA-Z0-9]+$"
    patrn_digits = "^[a-zA-Z]+$"
    try:
        request_json = request.json if request.json else \
            request.form if request.form.get(
                "short_name", False) else request.data
    except Exception as e:
        return forbidden(e.message)

    if not request_json.get('short_name', None):
        return forbidden("Not allowed.")

    short_name = str(request_json['short_name']).strip()
    request_json = json.dumps(request_json)
    error = ''
    reason = ''

    if not short_name:
        code = 200
        message = ''
        reason = ""
    elif not re.compile(patrn).match(short_name):
        code = 409
        if re.compile(patrn_space).match(short_name):
            error = 'space'
            message = 'Please remove spaces.'
        elif not re.compile(patrn_letter_number).match(short_name):
            error = 'disallowed_character'
            message = 'Short names can only have letters and numbers.'
        elif re.compile(patrn_digits).match(short_name):
            error = 'disallowed_character'
            message = 'Please add a four-digit year.'
        else:
            error = 'wrong_format'
            message = 'Short name format should be \'name\' + \
                \'four-digit-year\'.'
    elif Conference.query.filter_by(short_name=short_name).first():
        code = 409
        error = 'taken'
        message = 'Sorry, this name is already taken :('
    else:
        code = 200
        message = ''
    return jsonify(code=code, message=message,
                   reason=reason, error=error, request=request_json)


@api.route('/conf_admin/edit_conference_status', methods=['POST'])
@auth.login_required
@admin_required
def edit_conference_status():
    if request.json:
        conference = Conference.query.get_or_404(request.json['conf_id'])
        if request.json['new_status'] not in ['Approved', 'Denied']:
            return bad_request('Wrong status')
        conference.status = request.json['new_status']
        is_new_conf = request.json['is_new_conf']
        denial_msg = request.json.get('denial_msg')
        if conference.status == "Denied":
            conference.short_name = conference.short_name + '-denied'
            if not is_new_conf:
                for member in conference.members:
                    if member.curr_conf_id == conference.id:
                        member.curr_conf_id = 1
                        db.session.add(member)
        else:
            conference.short_name = conference.short_name.strip('-denied')
        try:
            db.session.add(conference)
            db.session.commit()
            if is_new_conf:
                conference.requester.join_conference(
                    conference,
                    role=Role.query.filter_by(name='Chair').first())
        except Exception as e:
            db.session.rollback()
            return internal_error(e.message)
        else:
            if is_new_conf:
                send_email(conference.requester.email,
                           'Conference Request (' +
                           conference.short_name.upper() + ')',
                           'email/conference_request_notification',
                           user=conference.requester,
                           conference=conference,
                           denial_msg=denial_msg)
                send_email(current_app.config['CONF_SUPPORT'],
                           'New conference request has been ' +
                           conference.status.lower(),
                           'email/conference_request_notification_admin',
                           conference=conference, denial_msg=denial_msg)
            else:
                send_email(conference.requester.email,
                           'Conference Request (' +
                           conference.short_name.upper() + ')',
                           'email/conference_request_notification',
                           user=conference.requester,
                           conference=conference, denial_msg=denial_msg)
                send_email(current_app.config['CONF_SUPPORT'],
                           'Conference request has been ' +
                           conference.status.lower(),
                           'email/conference_request_notification_admin',
                           conference=conference, denial_msg=denial_msg)
            return jsonify(conf_id=request.json['conf_id'],
                           new_status=request.json['new_status'])
    else:
        return bad_request('Not allowed for this content type:' +
                           request.headers['Content-Type'])


@api.route('/conferences/admin')
@auth.login_required
def conferences_admin():
    chair_role = Role.query.filter_by(name='Chair').first()
    conferences = Conference.query.filter(
        Conference.id == Track.conference_id,
        Track.id == JoinTrack.track_id,
        JoinTrack.role_id == chair_role.id,
        JoinTrack.user_id == current_user.id
    ).all()
    conferences_json = {}
    for conference in conferences:
        conferences_json[conference.short_name] = {
            'title': conference.name,
            'short_title': conference.short_name.upper(),
            'about': conference.info,
            'location': conference.city + ', ' +
            (conference.state + ', ' if conference.state else '') +
            conference.country,
            'venue': conference.address,
            'time': {
                'start': str(conference.start_date) + ' 00:00:00',
                'end': str(conference.end_date) + ' 00:00:00',
            },
            'type': 'conference',
            'important': True,
            'data_url': url_for('api.get_conference_schedule_app',
                                short_name=conference.short_name,
                                _external=True),
            'timezone': conference.timezone
        }
        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json?address=' +
            conference.address + ',' +
            conferences_json[conference.short_name]['location'])
        resp_json_payload = response.json()
        if resp_json_payload['status'] == 'OK':
            conferences_json[conference.short_name]['latitude'] = resp_json_payload['results'][0]['geometry']['location']['lat']
            conferences_json[conference.short_name]['longitude'] = resp_json_payload['results'][0]['geometry']['location']['lng']
    return jsonify(conferences_json)

@api.route('/conferences/admin/<short_name>')
@auth.login_required
def conference_admin(short_name):
    conference = Conference.query.filter(
        Conference.short_name == short_name).first()
    if not conference:
        return not_found('Not found')
    if not current_user.is_chair(conference):
        return forbidden('You do not have the permissions')
    papers = conference.get_papers.all()
    conference_json = {
        'short_name': conference.short_name,
        'submissions': len(papers),
        'accepted': len(filter(
            lambda paper: paper.status == PaperStatus.ACCEPTED, papers)),
        'rejected': len(filter(
            lambda paper: paper.status == PaperStatus.REJECTED, papers)),
        'under_review': len(filter(
            lambda paper: paper.status == PaperStatus.UNDER_REVIEW, papers)),
        'reviews':
        len(Review.query.filter_by(conference_id=conference.id).all())
    }
    additional_status_list = conference.configuration.get(
        'additional_status', '').split(',')
    conference_json['add_paper_status'] = {}
    for status in additional_status_list:
        if status:
            conference_json['add_paper_status'][status] = len(
                filter(lambda paper: paper.status == status, papers))
    review_assignments = db.session.query(paper_reviewer).filter(
            paper_reviewer.c.paper_id.in_(
                map(lambda paper: paper.id, papers))).all()
    conference_json['review_assignments'] = len(review_assignments)
    conference_json['no_assignment_paper'] = len(
        filter(lambda paper: paper.id not in map(
            lambda assignment: assignment.paper_id, review_assignments),
            papers))
    # conference_json['no_assignment_paper'] = len()
    return jsonify(conference_json)

@api.route('/conferences/<int:conference_id>/reports/author')
@auth.login_required
@chair_required
def get_report_author(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    default_track = conference.tracks.filter_by(default=True).first()
    papers = conference.get_papers.all()
    rows = []
    for pi, paper in enumerate(papers):
        authors_list = paper.authors_list.all()
        for author in authors_list:
            row_value = {
                'Full Name': author.full_name,
                'Affiliation': author.organization,
                'Email': author.email,
                'Country': author.country,
                'Paper ID': paper.id,
                'Paper Title': paper.title,
                'Paper Status': paper.status,
            }

            if author.is_registered_track(default_track):
                row_value['Registration Status'] = {
                    'value': '<i class="fa fa-check text-navy"></i>',
                    'options': {
                        'filterValue': 'Registered'
                    }
                }
            else:
                similar_users = conference.match_registration_record(author.user_id)
                if similar_users:
                    title = ', '.join([user.full_name + '(' + user.email + ')' for user in similar_users])
                    row_value['Registration Status'] = {
                        'value': '<label for="">Maybe registered</label>&nbsp;<i class="fa fa-question-circle" data-toggle="tooltip" data-placement="top" title="%s"></i>' % title,
                        'options': {
                            'filterValue': 'Unsure'
                        }
                    }
                else:
                    row_value['Registration Status'] = {
                        'value': '',
                        'options': {
                            'filterValue': 'Unregistered'
                        }
                    }

            if pi % 2:
                rows.append({
                    'options': {
                        'style': 'background-color: #F4F6FB;'
                    },
                    'value': row_value
                })
            else:
                rows.append(row_value)

    return Response(
        json.dumps(rows, separators=(',', ':')),  mimetype='application/json')


@api.route('/conferences/<int:conference_id>/reports/reviewer')
@auth.login_required
@chair_required
def get_report_reviewer(conference_id):
    display_option = request.args.get('display_option',
                                      'group_by_paper',
                                      type=str)
    conference = Conference.query.get_or_404(conference_id)
    default_track = conference.tracks.filter_by(default=True).first()
    if display_option == 'group_by_paper':
        papers = conference.get_papers.all()
        rows = []
        for pi, paper in enumerate(papers):
            reviews = paper.reviews.all()
            for review in reviews:
                row_value = {
                    'Full Name': review.reviewer.full_name,
                    'Affiliation': review.reviewer.organization,
                    'Email': review.reviewer.email,
                    'Country': review.reviewer.country,
                    'Registration Status': '<i class="fa fa-check text-navy"></i>' if review.reviewer.is_registered_track(default_track) else '',
                    'Paper ID': paper.id,
                    'Paper Title': paper.title,
                    'Paper Status': paper.status,
                    'Evaluation': review.evaluation,
                    'Confidence': review.confidence,
                    'Review': review.review_body
                }

                if pi % 2:
                    rows.append({
                        'options': {
                            'style': 'background-color: #F4F6FB;'
                        },
                        'value': row_value
                    })
                else:
                    rows.append(row_value)

        return Response(json.dumps(rows, separators=(',', ':')), mimetype='application/json')

    elif display_option == 'sort_by_papers_reviewed' or display_option == 'sort_by_review_quality':
        members = conference.members
        if display_option == 'sort_by_papers_reviewed':
            members_score_dict = {member.id: len(member.reviews.all()) for member in members}
        else:
            members_score_dict = {}
            for member in members:
                reviews = member.reviews.all()
                if not reviews:
                    continue
                total_words = len(
                    ''.join([r.review_body for r in reviews]))
                members_score_dict[member.id] = total_words / len(reviews)

        members = filter(lambda m: members_score_dict.get(m.id), members)
        members = sorted(members, key=lambda m: members_score_dict[m.id], reverse=True)

        rows = []
        for member in members:
            row = {
                'Full Name': member.full_name,
                'Affiliation': member.organization,
                'Email': member.email,
                'Country': member.country,
                'Papers Reviewed': members_score_dict[member.id],
                'Registration Status': '<i class="fa fa-check text-navy"></i>' if member.is_registered_track(default_track) else '',
            }
            rows.append(row)

        return Response(json.dumps(rows, separators=(',', ':')), mimetype='application/json')

    else:
        abort(400)


@api.route('/conferences/<int:conference_id>/reports/stat/<report_type>')
@auth.login_required
@chair_required
def get_report_statistics(conference_id, report_type):
    conference = Conference.query.get_or_404(conference_id)
    if report_type == 'author':
        papers = conference.get_papers.all()
        email_set = set()
        org_set = set()
        country_set = set()
        for paper in papers:
            users = paper.authors_list.all()
            for user in users:
                email_set.add(user.email)
                country_set.add(user.country)
                org_set.add(user.organization)
        summary = {
            'email_num': len(email_set),
            'country_num': len(country_set),
            'org_num': len(org_set)
        }
    elif report_type == 'reviewer':
        members = conference.members
        members = filter(lambda m: m.reviews.first(), members)
        summary = {
            'email_num': len(set([m.email for m in members])),
            'country_num': len(set([m.country for m in members])),
            'org_num': len(set([m.organization for m in members]))
        }
    elif report_type == 'paper':
        papers = conference.get_papers.all()
        org_set = set()
        country_set = set()
        for paper in papers:
            users = paper.authors_list.all()
            for user in users:
                country_set.add(user.country)
                org_set.add(user.organization)
        summary = {
            'email_num': len(papers),
            'country_num': len(country_set),
            'org_num': len(org_set)
        }
    else:
        return bad_request('Invalid report')
    return jsonify(summary)


@api.route('/conferences/<int:conference_id>/review_assignment_excel',
           methods=['GET'])
@auth.login_required
def download_review_assignment_excel(conference_id):
    """Download excel for review assignment import."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.can(Permission.MANAGE_REVIEW, conference):
        return forbidden('Not allowed')
    # check parameter value
    try:
        num_reviewers = int(request.args.get('reviewers', False))
    except Exception:
        return bad_request('Value of number of reviewers is invalid')
    if num_reviewers < 1 or num_reviewers > 10:
        return bad_request('Value of number of reviewers is invalid')
    # generate excel file
    output = StringIO.StringIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('assignments_list')
    worksheet_pc = workbook.add_worksheet('reviewers_list')
    # Add a format for the header cells.
    header_format = workbook.add_format({
        'border': 1,
        'bg_color': '#1ab394',
        'bold': True,
        'text_wrap': False,
        'valign': 'vcenter',
        'indent': 1,
    })
    # unlocked = workbook.add_format({'locked': 0})
    # fill the pc sheet
    reviewers = conference.reviewers
    total_reviewers = len(reviewers)
    for index, reviewer in enumerate(reviewers):
        worksheet_pc.write(
            index, 0, reviewer.id)
        worksheet_pc.write(
            index, 1,
            '{} ({}) {{{}}}'.format(reviewer.full_name.encode('utf-8'),
                                    reviewer.email,
                                    reviewer.id).decode('utf-8'))
    # cleanup reviewers
    for reviewer in reviewers:
        if len(reviewer.review_assignment_conference(
            conference)) >= int(conference.configuration.get(
                'max_paper', sys.maxsize)):
            reviewers.remove(reviewer)
    # track chair??
    papers = conference.get_papers.all()
    worksheet.write(0, 0, 'ID', header_format)
    worksheet.write(0, 1, 'Title', header_format)
    worksheet.write(0, 2, 'Authors', header_format)
    for i in range(num_reviewers):
        worksheet.write(0, i + 3, 'Reviewer ' + str(i + 1), header_format)
    for index in range(len(papers)):
        worksheet.write(index + 1, 0, papers[index].id)
        worksheet.write(index + 1, 1, papers[index].title)
        worksheet.write(
            index + 1, 2,
            ', '.join('{}({})'.format(
                author.full_name.encode('utf-8'),
                author.organization.encode('utf-8')
            ) for author in papers[index].authors_list).decode('utf-8'))
        if request.args.get('auto_assignment', 'false') == 'true':
            # auto assignment
            temp_reviewer_list = []
            for i in range(num_reviewers):
                counter = 0
                while counter < 5:
                    shuffle(reviewers)
                    _reviewer = choice(reviewers)
                    if papers[index].check_review_conflict(
                            _reviewer,
                            check_author=True,
                            check_reviewer=True)[0] and \
                            _reviewer not in temp_reviewer_list:
                        worksheet.write(
                            index + 1,
                            3 + i,
                            '{} ({}) {{{}}}'.format(
                                _reviewer.full_name.encode('utf-8'),
                                _reviewer.email,
                                _reviewer.id).decode('utf-8'))
                        temp_reviewer_list.append(_reviewer)
                        if len(_reviewer.review_assignment_conference(
                            conference)) >= int(conference.configuration.get(
                                'max_paper', sys.maxsize)):
                            reviewers.remove(_reviewer)
                        break
                    else:
                        counter += 1
    # worksheet.protect()
    worksheet.data_validation(
        1, 3, len(papers), num_reviewers + 2,
        {
            'validate': 'list',
            'source': '=reviewers_list!$B$1:$B${}'.format(total_reviewers),
            'input_title': 'Select a reviewer in the list',
        })
    worksheet_pc.protect()
    workbook.close()
    output.seek(0)
    response = Response(
        output.read(),
        mimetype=('application/vnd.openxmlformats-offi'
                  'cedocument.spreadsheetml.sheet'),
        headers={
            'Content-Disposition':
            'attachment;filename={}_review_assignments.xlsx'.format(
                conference.short_name)})
    return response
