from .. import db
from flask_login import current_user
from ..models import Conference, Registration
from . import api
from .errors import forbidden
from ..utils.macros import byteify
from flask import request
from collections import OrderedDict
from .authentication import auth


@api.route('/registrations/<int:id>')
def get_registration(id):
    pass
# ticket = Registration.query.get_or_404(id)
# return jsonify(ticket.to_json())


@api.route('/registrations/<int:conference_id>', methods=['PUT'])
@auth.login_required
def update_registration(conference_id):
    registration = Conference.query.get_or_404(conference_id).registration
    if not current_user.is_chair(registration.conference):
        return forbidden('Not allowed')
    configuration_setting = byteify(request.json.get('configuration_setting'))
    payout = request.json.get('payout')
    if configuration_setting:
        temp_configuration_setting = {
            'instruction': configuration_setting['instruction'],
            'questions': []
        }
        for q in configuration_setting['questions']:
            q['id'] = str(q['id'])
        if len(registration.private_question):
            # print len(registration.private_question)
            # print configuration_setting['questions']
            private_questions = OrderedDict()
            for i in configuration_setting['questions']:
                if i['private'] == "true":
                    private_questions[str(i['id'])] = i
                else:
                    temp_configuration_setting['questions'].append(i)
            registration.private_question = private_questions
        else:
            temp_configuration_setting[
                'questions'] = configuration_setting['questions']
            # print '***************'
            # configuration_setting['questions'][:-len(registration.private_question)]
            # configuration_setting['questions'][-len(registration.private_question):]
        registration.configuration_setting = temp_configuration_setting
        # print registration.private_question
        # else:
        # handle no private question
        # print configuration_setting['questions']
        # temp_configuration_setting['questions'] = configuration_setting['questions']
        # registration.configuration_setting = temp_configuration_setting
    if payout:
        registration.payout = {k: v for d in payout for k, v in d.items()}
        registration.payout['status'] = 'Pending'
        # registration.payout = temp_payout
    db.session.add(registration)
    db.session.commit()
    # print registration.configuration_setting
    # print registration.private_question
    return 'Success', 200


@api.route('/registrations/<int:id>', methods=['PUT'])
@auth.login_required
def update_registration_form(id):
    pass


# @api.route('/registrations/<int:registration_id>/net_sale')
# @auth.login_required
# def check_net_sale(transaction_id):
#     registration = Registration.query.get_or_404(id)
#     if not current_user.is_chair(registration.conference):
#         return forbidden('Not allowed')
#
