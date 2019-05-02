from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import Ticket, Conference, TicketTransaction, TicketPrice, \
    TicketStatus
from . import api
from .errors import bad_request, not_acceptable, forbidden
from datetime import datetime
from .authentication import auth


@api.route('/tickets/<id>')
def get_ticket(id):
    if id != 'undefined':
        ticket = Ticket.query.get_or_404(id)
        return jsonify(ticket.to_json())
    else:
        return 'Ticket id is empty', 204


@api.route('/conferences/<int:id>/tickets')
@auth.login_required
def get_tickets(id):
    conference = Conference.query.get_or_404(id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    tickets = conference.registration.tickets.all()
    return jsonify({'tickets': [ticket.to_json() for ticket in tickets]})


@api.route('/conferences/<int:id>/tickets', methods=['PUT'])
@auth.login_required
def update_tickets(id):
    conference = Conference.query.get_or_404(id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    for ticket_dict in request.json['update_tickets']:
        ticket = conference.registration.tickets.filter_by(
            id=ticket_dict['ticket_id']).first()
        if ticket:
            ticket.name = ticket_dict['ticket_title']
            try:
                ticket.start_date = datetime.strptime(
                    ticket_dict['start_date'], "%Y-%m-%d").date()
                ticket.end_date = datetime.strptime(
                    ticket_dict['end_date'], "%Y-%m-%d").date()
            except ValueError:
                return not_acceptable('Wrong value')
            for k, v in sorted(ticket_dict['ticket_price'].iteritems()):
                price = ticket.prices.filter_by(currency=k).first()
                if price:
                    price.amount = v
                else:
                    price = TicketPrice(currency=k, amount=v)
                    ticket.prices.append(price)
                db.session.add(price)
            db.session.add(ticket)
        else:
            db.session.rollback()
            return not_acceptable('Wrong value')
    try:
        db.session.commit()
        return 'Success', 200
    except Exception:
        db.session.rollback()
        return bad_request('Cannot be updated.')


@api.route('/conferences/<int:id>/tickets', methods=['DELETE'])
@auth.login_required
def delete_tickets(id):
    conference = Conference.query.get_or_404(id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    for ticket_id in request.json['delete_tickets']:
        ticket = conference.registration.tickets.filter_by(
            id=ticket_id).first()
        if ticket:
            ticket.status = TicketStatus.DELETED
            db.session.add(ticket)
        else:
            db.session.rollback()
            return not_acceptable('Wrong value')
    db.session.commit()
    return 'Success', 200


@api.route('/conferences/<int:id>/tickets', methods=['POST'])
@auth.login_required
def add_tickets(id):
    conference = Conference.query.get_or_404(id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    response_json = []
    # print request.json['num_of_tracks']
    for add_ticket in request.json['add_tickets']:
        try:
            ticket = Ticket(name=add_ticket['name'],
                            start_date=datetime.strptime(
                                add_ticket['start_date'], "%Y-%m-%d").date(),
                            end_date=datetime.strptime(
                                add_ticket['end_date'], "%Y-%m-%d").date(),
                            registration_id=conference.registration.id)
            # for price in add_ticket['price'].
            for k, v in sorted(add_ticket['price'].iteritems()):
                price = TicketPrice(currency=k, amount=v)
                db.session.add(price)
                ticket.prices.append(price)
        except ValueError:
            return not_acceptable('Wrong value')
        try:
            db.session.add(ticket)
            # must commit every time to get the id
            db.session.commit()
            response_json.append((add_ticket['ticket_div_id'], ticket.id))
        except Exception:
            db.session.rollback()
            return bad_request('Cannot be added.')
    # return the id and name of the tracks
    return jsonify(response_json)


@api.route('/conferences/<int:conference_id>/ticketsale')
@auth.login_required
def get_ticketsale(conference_id):
    """Return the sales data for chart."""
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    tickets = conference.registration.tickets.filter(
        Ticket.number_of_sold > 0).all()
    # get the ticket sale number pie chart for a conference
    chart_json = {}
    pie_json = {}
    types = [ticket.name for ticket in tickets]
    nums = [ticket.number_of_sold for ticket in tickets]
    pie_json['types'] = types
    pie_json['nums'] = nums
    chart_json['pie'] = pie_json
    # get the ticket sales history for a conference
    dates = []
    sales = []
    for ticket_transaction in conference.registration\
            .get_ticket_transactions.order_by(
                TicketTransaction.timestamp).all():
        date = ticket_transaction.timestamp.date().strftime('%Y/%m/%d')
        if date not in dates:
            dates.append(date)
            sales.append(
                ticket_transaction.balance_transaction_amount if
                ticket_transaction.balance_transaction_amount > 0 else 0)
        else:
            sales[dates.index(date)] += ticket_transaction.balance_transaction_amount if \
                ticket_transaction.balance_transaction_amount > 0 else 0
    linechart_json = {'dates': dates, 'sales': sales}
    chart_json['linechart'] = linechart_json
    return jsonify(chart_json)
