from flask import jsonify
from ..models import TicketPrice
from . import api


@api.route('/ticket_prices/<int:id>')
def get_ticket_price(id):
    ticket_price = TicketPrice.query.get_or_404(id)
    return jsonify(ticket_price.to_json())
