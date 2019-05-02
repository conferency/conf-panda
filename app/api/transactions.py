from json import dumps

from flask import jsonify, request, Response, url_for, redirect
from flask_login import current_user

from . import api
from .authentication import auth
from .errors import forbidden
from .. import db
from ..models import TicketTransaction


@api.route('/transactions/')
@auth.login_required
def get_transaction_redirect():
    transaction = TicketTransaction.query.get_or_404(request.args['id'])
    if not current_user.is_chair(transaction.registration.conference):
        return forbidden('Not allowed')
    return redirect(url_for('api.get_transaction', id=request.args['id']))


@api.route('/transactions/<int:id>')
@auth.login_required
def get_transaction(id):
    transaction = TicketTransaction.query.get_or_404(id)
    if not current_user.is_chair(transaction.registration.conference):
        return forbidden('Not allowed')
    return jsonify(transaction.to_json())


@api.route('/transactions/edit', methods=['POST'])
@auth.login_required
def edit_transaction():
    if not request.json \
            or 'ticket_transaction_id' not in request.json\
            or 'first_name' not in request.json \
            or 'last_name' not in request.json \
            or 'email' not in request.json \
            or 'affiliation' not in request.json:
        return 'Bad request', 400
    else:
        id = request.json['ticket_transaction_id']
        transaction = TicketTransaction.query.get_or_404(id)
        if not current_user.is_chair(transaction.registration.conference):
            return forbidden('Not allowed')
        transaction.attendee_info['First Name'] = request.json['first_name']
        transaction.attendee_info['Last Name'] = request.json['last_name']
        transaction.attendee_info['Email'] = request.json['email']
        transaction.attendee_info['Affiliation'] = request.json['affiliation']

        db.session.add(transaction)
        db.session.commit()

    return jsonify(transaction.to_json())


@api.route('/transactions/user/<int:user_id>/')
@auth.login_required
def show_tickets(user_id):
    """Return json file of tickets."""
    if current_user.id != user_id:
        return forbidden("Not accessiable")
    transaction_list = []
    for transaction in current_user.ticket_transactions.all():
        transaction_json = {
            'conference': transaction.registration.conference.name,
            'title': transaction.tickets[0].name, 'qty': 1,
            'price': str(transaction.subtotal) + ' ' + transaction.currency,
            'date': str(transaction.timestamp),
            'payment': transaction.status,
            'invoice': '<a href="' +
            url_for('conference.transaction_invoice',
                    conference_id=transaction.registration.conference_id,
                    transaction_id=transaction.id) +
            '" class="btn-tab-sm" target="_blank"><i class="fa fa-pencil"></i> \
            Print Invoice</a>',
            'hide': '<b>First Name: </b>' +
            transaction.attendee_info['First Name'] +
            '<br><b>Last Name: </b>' +
            transaction.attendee_info['Last Name'] + '<br><b>Email: </b>' +
            transaction.attendee_info['Email'] + '<br><b>Affiliation: </b>' +
            transaction.attendee_info['Affiliation'] + '<br>'
        }
        for question in transaction.registration.validate_questions:
            transaction_json['hide'] += '<b>' +\
                question['desc'] + ': </b>' + \
                (', '.join(transaction.attendee_info.get(
                    question['id'], '')) if question['ques_type'] == 1
                    else transaction.attendee_info.get(question['id'], '')) + \
                '<br>'
        transaction_list.append(transaction_json)
    return Response(dumps(transaction_list),  mimetype='application/json')
