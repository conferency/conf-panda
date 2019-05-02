# -*- coding: utf-8 -*-
"""Apis __init__ ."""

from flask import Blueprint, request, jsonify

api = Blueprint('api', __name__)

from . import authentication, posts, users, comments, errors, papers, \
    configurations, conferences, tracks, roles, email_templates, tickets, \
    registrations, customized_questions, promo_codes, products, \
    payouts, pages, support_email, session, todos, website, paper_bidding, \
    conference_schedules, sessions, transactions, invitations, \
    review_preferences, conference_promos, conference_addons, review, \
    fav_sessions, ticket_prices, review_assignments, conference_transactions, \
    product_options, email_preview, testing_email


@api.errorhandler(404)
def not_found(error=None):
    message = {
        'status': 404,
        'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404
    return resp
