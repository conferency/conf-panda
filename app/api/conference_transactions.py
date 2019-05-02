# -*- coding: utf-8 -*-
"""Restful api for conference transaction."""

from flask import request
from datetime import datetime
from .. import db
from ..models import ConferenceTransaction, User
from . import api
from .decorators import admin_required
from .authentication import auth
from .errors import bad_request
from ..utils.email_operation import send_email
# from ..utils.stripeHelper import refund
from ..utils.event_log import add_event


@api.route('/admin/transactions/resend', methods=['POST'])
@auth.login_required
@admin_required
def resend_conference_transaction_email():
    """Resend transactions email."""
    transaction = ConferenceTransaction.query.get(
        request.json.get('transaction_id'))
    if transaction:
        conference = transaction.conference_payment.conference
        payer = User.query.get(transaction.payer_id)
        card_info = transaction.conference_payment.card_info.values()[0]
        send_email(
            payer.email,
            'Receipt for ' + conference.short_name.upper(),
            'email/conference_payment_receipt',
            conference=conference,
            title='Receipt for ' + conference.short_name.upper(),
            promo_code=transaction.promo_code,
            addons=transaction.addons.all(),
            card_number=card_info['card_number'],
            holder_name=card_info['holder_name'],
            price=transaction.amount,
            currency='USD')
        return 'Success', 200
    else:
        return bad_request('Cannot resend.')


@api.route('/admin/transactions/refund', methods=['POST'])
@auth.login_required
@admin_required
def refund_conference_transaction():
    """Refund conference transaction."""
    transaction = ConferenceTransaction.query.get(
        request.json.get('transaction_id'))
    if transaction:
        # refund
        try:
            transaction.refund_transaction()
        except Exception as e:
            return bad_request(e.message)

        conference = transaction.conference_payment.conference
        # check if conference is free
        # conference.type = 'Free'
        payer = User.query.get(transaction.payer_id)
        card_info = transaction.conference_payment.card_info.values()[0]
        send_email(
            payer.email,
            'Refund for ' + conference.short_name.upper(),
            'email/conference_payment_receipt',
            conference=conference,
            title='Refund for ' + conference.short_name.upper(),
            promo_code=transaction.promo_code,
            addons=transaction.addons.all(),
            card_number=card_info['card_number'],
            holder_name=card_info['holder_name'],
            price=transaction.amount,
            refund=True,
            currency='USD')
        add_event('Refund ' + str(transaction.amount) + ' USD to ' +
                  card_info['holder_name'],
                  ', '.join([addon.name + ' ($' + str(addon.price) +
                            ')' for addon in transaction.addons]),
                  conference_id=conference.id,
                  type='conference_transactions_refund')
        return 'Success', 200
    else:
        return bad_request('Cannot refund.')
