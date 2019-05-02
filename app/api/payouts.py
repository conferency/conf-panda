from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import Conference
from . import api
from .decorators import admin_required
from datetime import datetime
from .authentication import auth
from .errors import forbidden


@api.route('/conferences/<int:conference_id>/payouts', methods=['PUT'])
@auth.login_required
def update_payout(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    payout = conference.registration.payout
    if request.json and payout.status != 'Completed':
        payout.account_name = request.json.get('account_name')
        payout.street_1 = request.json.get('address_1')
        payout.street_2 = request.json.get('address_2')
        payout.city = request.json.get('city')
        payout.state = request.json.get('state')
        payout.country = request.json.get('country')
        payout.zipcode = request.json.get('zipcode')
        payout.payment_method = request.json.get('payment_method')
        payout.bank_name = request.json.get('bank_name')
        payout.account_type = request.json.get('account_type')
        payout.routing_number = request.json.get('routing_number')
        payout.account_number = request.json.get('account_number')
        db.session.add(payout)
        db.session.commit()
        return 'Success', 200
    else:
        return 'Bad request', 400


@api.route('/conferences/<int:conference_id>/payouts/pay', methods=['PUT'])
@auth.login_required
@admin_required
def update_payout_pay(conference_id):
    payout = Conference.query.get_or_404(conference_id).registration.payout
    if request.json and (request.json.get('payout_status') == 'Pending' or request.json.get('payout_status') == 'Completed'):
        payout.status = request.json.get('payout_status')
        payout.amount = request.json.get('payout_amount')
        payout.note = request.json.get('payout_note')
        payout.update_timestamp = datetime.utcnow()
        db.session.add(payout)
        db.session.commit()
        return jsonify({'last_updated': str(datetime.utcnow().strftime("%B %d, %Y"))})
    else:
        return 'Bad request', 400
