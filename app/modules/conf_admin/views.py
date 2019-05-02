# -*- coding: utf-8 -*-
"""Admin module for conferency."""

import errno
import os
from datetime import datetime
from flask import render_template, request, current_app, session, redirect, \
    url_for, flash
from flask.ext.login import login_user, logout_user, current_user
from sqlalchemy import or_, and_
from . import conf_admin
from ...models import Conference, User, Paper, ConferencePromoCode, \
    ConferenceAddon, Ticket
from ...utils.decorators import admin_required


@conf_admin.route('/dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    pending_conferences = len(
        Conference.query.filter(Conference.status == 'Pending').all())
    approved_conferences = len(
        Conference.query.filter(Conference.status == 'Approved').all())
    ongoing_conferences = len(
        Conference.query.filter(Conference.end_date > datetime.utcnow()).all())
    conferences = Conference.query.filter(
        Conference.id != 1 and Conference.status == 'Approved').all()
    total_users = len(User.query.filter_by(confirmed=True).all())
    total_papers = len(Paper.query.all())
    pending_payout = 0
    for conference in conferences:
        if conference.registration.payout.status == 'Pending' and \
                conference.registration.total_sold != 0:
            pending_payout += 1
    return render_template('conf_admin/admin_dashboard.html',
                           pending_conferences=pending_conferences,
                           ongoing_conferences=ongoing_conferences,
                           approved_conferences=approved_conferences,
                           pending_payout=pending_payout,
                           total_users=total_users,
                           total_papers=total_papers)


@conf_admin.route('/conferences/requests', methods=['GET', 'POST'])
@admin_required
def admin_requests():
    # might be faster with using python sort??
    pending_conferences = Conference.query.filter_by(
        status='Pending').order_by(Conference.request_time.desc()).all()
    approved_conferences = Conference.query.filter_by(
        status='Approved').order_by(Conference.request_time.desc()).all()
    denied_conferences = Conference.query.filter_by(
        status='Denied').order_by(Conference.request_time.desc()).all()
    ongoing_conferences = Conference.query.filter(
        Conference.end_date > datetime.utcnow()).order_by(
        Conference.start_date.asc()).all()
    return render_template('conf_admin/admin_requests.html',
                           pending_conferences=pending_conferences,
                           approved_conferences=approved_conferences,
                           denied_conferences=denied_conferences,
                           ongoing_conferences=ongoing_conferences)


@conf_admin.route('/conferences/<int:conference_id>', methods=['GET'])
@admin_required
def conferences_detail(conference_id):
    """Details of the conference."""
    conference = Conference.query.get_or_404(conference_id)
    conference_stat = {
        'submission': {
            'all': len(conference.get_papers.all()),
            'Withdrawn': len(conference.get_papers_status('Withdrawn')),
            'Deleted': len(conference.get_papers_status('Deleted'))
        },
        'review': {
            'all': len(conference.reviews.all())
        },
        'member': {
            'all': len(conference.members),
            'chair': len(conference.chairs),
            'pc': len(conference.pcs)
        },
        'registration': {
            'all': '',
            'ticket': [],
            'ticket_stat': []
        }
    }
    for ticket in conference.registration.tickets.filter(
            Ticket.status != 'Deleted').all():
        conference_stat['registration']['ticket'].append(ticket.name)
        conference_stat['registration']['ticket_stat'].append(
            ticket.number_of_sold)
    conference_stat['registration']['all'] = sum(
        conference_stat['registration']['ticket_stat'])
    transactions = conference.conference_payment.transactions.all()
    return render_template('conf_admin/conference_detail.html',
                           conference=conference,
                           conference_stat=conference_stat,
                           transactions=transactions)


@conf_admin.route('/conferences/registrations', methods=['GET'])
@admin_required
def admin_registrations():
    conferences = Conference.query.filter(Conference.id != 1).all()
    return render_template('conf_admin/admin_registrations.html',
                           conferences=conferences)


@conf_admin.route('/conferences/<int:conference_id>/registrations',
                  methods=['GET', 'POST'])
@admin_required
def admin_conf_registration(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conf_admin/admin_conf_registration.html',
                           conference=conference)


@conf_admin.route('/masquerade/<int:user_id>', methods=['GET'])
@admin_required
def masquerade(user_id):
    """Allow admin to masquerade a user."""
    user = User.query.get_or_404(user_id)
    session['masqueraded'] = True
    session['origin'] = current_user.id
    login_user(user, False)
    return redirect(url_for('main.dashboard'))


@conf_admin.route('/masquerade/<int:user_id>/exit', methods=['GET'])
def masquerade_exit(user_id):
    logout_user()
    session.pop('masqueraded', None)
    session.pop('origin', None)
    flash('For your security, please log in again.')
    return redirect(url_for('auth.login'))


@conf_admin.route('/paper_json', methods=['POST'])
def json_upload():
    conference = Conference.query.get_or_404(request.form['conference_id'])
    # docs = request.files.getlist('paper')
    path = os.path.join(current_app.config['UPLOADED_PAPERS_DEST'],
                        conference.short_name)
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
        else:
            pass
    # # print request.files['paper_json'].filename
    request.files['paper_json'].save(os.path.join(path, 'paper_json.json'))
    return 'Success', 201


@conf_admin.route('/conference_pricing')
def conference_pricing():
    promo_codes = ConferencePromoCode.query.all()
    addons = ConferenceAddon.query.all()
    return render_template('conf_admin/admin_conference_pricing.html',
                           addons=addons,
                           promo_codes=promo_codes)


@conf_admin.route('/conference_all')
def conference_all():
    """Return all joined conferences."""
    page = request.args.get('page', 1, type=int)
    keywords = request.args.get('keyword', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    empty_flag = False
    result_count = -1
    conference_query = Conference.query

    # search bar has been commented out
    if keywords == '' and location == '' and \
            start_date == '' and end_date == '':
        pagination = conference_query.order_by(
            Conference.start_date.desc()).paginate(
            page,
            per_page=20,
            error_out=False)
        conferences = [
            conference for conference in pagination.items if conference.status == 'Approved']
        result_count = len(conferences)
    else:
        # deprecated
        if start_date != '' and end_date != '':
            conferences_result_date = conference_query.filter(and_(
                Conference.start_date >= start_date,
                Conference.end_date <= end_date))

        elif start_date == '' and end_date == '':
            conferences_result_date = conference_query

        elif start_date == '':
            conferences_result_date = conference_query.filter(
                Conference.end_date <= end_date)
        elif end_date == '':
            conferences_result_date = conference_query.filter(
                Conference.start_date >= start_date)
        pagination = conferences_result_date.paginate(
            page,
            per_page=15,
            error_out=False)
        conferences = [conference for conference in pagination.items]
        conferences_result = conferences_result_date.filter(
            or_(Conference.city.contains(location),
                Conference.state.contains(location),
                Conference.country.contains(location))).filter(
            or_(Conference.name.contains(keywords),
                Conference.short_name.contains(keywords),
                Conference.address.contains(keywords),
                Conference.tags.contains(keywords),
                Conference.subjects.contains(keywords),
                Conference.info.contains(keywords),
                Conference.website.contains(keywords)
                ))
        result_count = len(conferences_result.all())
        if not result_count:
            pagination = conference_query.with_entities(Conference.id,
                                                        Conference.name,
                                                        Conference.short_name,
                                                        Conference.address,
                                                        Conference.city,
                                                        Conference.state,
                                                        Conference.country,
                                                        Conference.start_date,
                                                        Conference.end_date,
                                                        Conference.status
                                                        ).order_by(
                Conference.start_date.desc()).paginate(page,
                                                       per_page=15,
                                                       error_out=False)
            conferences = [
                conference for conference in pagination.items if conference.status == 'Approved']
            result_count = len(conferences)
            empty_flag = True
        else:
            pagination = conferences_result.paginate(page,
                                                     per_page=15,
                                                     error_out=False)
        conferences = [
            item.conference for item in pagination.items if item.conference.status == 'Approved']
        # return redirect()
    # else:
    #     abort(404)
    today = datetime.today()
    conferences_notexpired = conference_query.filter(Conference.end_date >= today).order_by(
        Conference.start_date.asc()).all()
    conferences_expired = conference_query.filter(Conference.end_date < today).order_by(
        Conference.start_date.desc()).all()
    return render_template('conf_admin/admin_all_conference.html',
                           empty_flag=empty_flag,
                           conferences_notexpired=conferences_notexpired,
                           conferences_expired=conferences_expired,
                           result_count=result_count, pagination=pagination,
                           keywords=keywords,
                           location=location, start_date=start_date,
                           end_date=end_date)
