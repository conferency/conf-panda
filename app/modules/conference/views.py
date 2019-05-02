# -*- coding: utf-8 -*-
"""View functions for conference."""

import datetime
import json
import os
import re
import sys
# import math
from collections import OrderedDict
# from Queue import PriorityQueue
from random import shuffle, sample
from flask import render_template, redirect, request, url_for, flash, \
    current_app, abort, send_file, jsonify
from flask.ext.login import login_required, current_user
from sqlalchemy import or_, and_
from wtforms import StringField, SelectMultipleField, BooleanField, \
    SelectField, HiddenField
from wtforms.validators import required, email
from wtforms_dynamic_fields import WTFormsDynamicFields
# temp
# from threading import Thread
from app.utils.regex import check_name
from . import conference
from .forms import ConferenceEditForm, ConferenceForm, NotificationForm, \
    RegistrationForm, InvitationsForm, TrackNotificationForm, \
    AutomaticAssignmentForm, PayoutForm
from ..submission.forms import PaperForm
from ... import APP_STATIC
from ... import db
from ...models import Conference, Author, User, Paper, Permission, Track, \
    JoinTrack, Role, TicketPrice, TicketTransaction, TransactionStatus, \
    Product, ProductOption, PromoCode, Invitation, EventLog, PaperStatus, \
    DelegateReview, EmailTemplate, paper_reviewer, Review, \
    UserDoc, ConferencePayment, ConferenceAddon, \
    ConferencePromoCode, PaperBidding
from ...utils.decorators import permission_required, chair_required
# temp
from ...utils.email_operation import send_email
from ...utils.event_log import add_event
from ...utils.macros import check_date
from ...utils.stripeHelper import generate_customer, charge, get_net
from ...utils.template_convert import template_convert
from ...utils.website import wordpress_create_site


@conference.route('/')
@login_required
def my_conference():
    """Return all joined conferences."""
    page = request.args.get('page', 1, type=int)
    keywords = request.args.get('keyword', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    empty_flag = False
    result_count = -1
    conference_query = Conference.query.join(
        Track, Track.conference_id == Conference.id).join(
        JoinTrack, JoinTrack.track_id == Track.id).filter(
        and_(JoinTrack.user_id == current_user.id,
             Conference.status == 'Approved'))

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
    today = datetime.date.today()
    conferences_notexpired = conference_query.filter(Conference.end_date >= today).order_by(
        Conference.start_date.asc()).all()
    conferences_expired = conference_query.filter(Conference.end_date < today).order_by(
        Conference.start_date.desc()).all()
    return render_template('conference/conference_my.html',
                           empty_flag=empty_flag,
                           conferences_notexpired=conferences_notexpired,
                           conferences_expired=conferences_expired,
                           result_count=result_count, pagination=pagination,
                           keywords=keywords,
                           location=location, start_date=start_date,
                           end_date=end_date)


@conference.route('/request', methods=['GET'])
@login_required
def request_conference():
    """Request conference."""
    # get the conferences pending:
    conferences = current_user.create_conferences.order_by(
        Conference.request_time.desc()).all()
    return render_template('conference/conference_request.html',
                           conferences=conferences)


@conference.route('/request_new/<type>', methods=['GET', 'POST'])
@login_required
def request_new_conference(type):
    professional_addon = ConferenceAddon.query.filter_by(
        name='Professional Base Fee').first()
    if type == 'new':
        return render_template('conference/conference_request_new.html',
                               price=professional_addon.price)
    elif type == 'free' or type == 'pro':
        if type == 'pro':
            # add fields
            setattr(ConferenceForm,
                    'card_number',
                    StringField('Credit card number *',
                                validators=[required()]))
            setattr(ConferenceForm,
                    'holder_name',
                    StringField('Name on card *', validators=[required()]))
            setattr(ConferenceForm,
                    'stripeToken',
                    HiddenField())
            setattr(ConferenceForm,
                    'security_code',
                    StringField('CVC *', validators=[required()]))
            setattr(ConferenceForm,
                    'month',
                    SelectField('Month *',
                                validators=[required()],
                                choices=[('1', 'Jan'), ('2', 'Feb'),
                                         ('3', 'Mar'), ('4', 'Apr'),
                                         ('5', 'May'), ('6', 'June'),
                                         ('7', 'July'), ('8', 'Aug'),
                                         ('9', 'Sept'), ('10', 'Oct'),
                                         ('11', 'Nov'), ('12', 'Dec')]))
            setattr(ConferenceForm,
                    'year',
                    SelectField('Year *',
                                validators=[required()],
                                choices=[('2018', '2018'),
                                         ('2019', '2019'), ('2020', '2020'),
                                         ('2021', '2021'), ('2022', '2022'),
                                         ('2023', '2023'), ('2024', '2024'),
                                         ('2025', '2025'), ('2026', '2026'),
                                         ('2027', '2027'), ('2028', '2028')]))
        form = ConferenceForm()
        if request.method == 'POST':
            if form.validate_on_submit():
                # convert list to string
                conference = Conference(
                    name=form.conference_name.data,
                    short_name=form.short_name.data.lower(),
                    contact_email=form.contact_email.data,
                    contact_phone=form.contact_phone.data,
                    website=form.website_url.data,
                    address=form.address.data,
                    city=form.city.data,
                    state=form.state.data,
                    country=form.country.data,
                    start_date=form.start.data,
                    end_date=form.end.data,
                    timezone=form.timezone.data,
                    info=form.info.data,
                    subjects=';'.join(form.subjects.data),
                    requester_id=current_user.id,
                    tags=form.tags.data,
                    requester_info=OrderedDict([
                        ('Your role', form.your_role.data),
                        ('Name', form.contact_name.data),
                        ('Affiliation', form.affiliation.data),
                        ('Phone number', form.requester_contact_phone.data),
                        ('Website', form.requester_website.data),
                        ('How did you hear about us?', form.source_from.data),
                        ('Referred by', form.referred_by.data)]))
                if type == 'pro':
                    promo_code = ConferencePromoCode.validate_promo_code(
                        request.form.get('promo_code'))
                    try:
                        customer_id = generate_customer(
                            email=form.contact_email.data,
                            source=form.stripeToken.data,
                            name=form.holder_name.data)
                        if promo_code:
                            if promo_code.type == 'fixed_amount':
                                price = professional_addon.price - \
                                    promo_code.value
                            else:
                                price = professional_addon.price * (
                                    1 - promo_code.value / 100)
                            promo_code.usage += 1
                            db.session.add(promo_code)
                        else:
                            price = professional_addon.price
                        conference.type = 'Professional'
                        default_conference_payment = ConferencePayment(
                            stripe_customer_id=customer_id,
                            card_info={
                                form.card_number.data: {
                                    'card_number': form.card_number.data,
                                    'holder_name': form.holder_name.data,
                                    'security_code': form.security_code.data,
                                    'year': form.year.data,
                                    'month': form.month.data
                                }
                            },
                            total=professional_addon.price,
                            charged=professional_addon.price
                        )
                        # add_transaction has commit
                        if price > 0:
                            charge_id, balance_transaction_id = charge(
                                customer_id=customer_id,
                                amount=price,
                                description='Professional setup fee for ' +
                                            conference.short_name)
                            default_conference_payment.add_transaction(
                                payer_id=current_user.id,
                                charge_id=charge_id,
                                balance_transaction_id=balance_transaction_id,
                                addon_id=professional_addon.id,
                                promo_code_id=promo_code.id if promo_code
                                else None,
                                amount=price)
                        # send receipt
                        send_email(
                            current_user.email,
                            'Receipt for ' + conference.short_name.upper(),
                            'email/conference_payment_receipt',
                            conference=conference,
                            title='Receipt for ' +
                            conference.short_name.upper(),
                            addons=[professional_addon],
                            promo_code=promo_code,
                            card_number=form.card_number.data,
                            holder_name=form.holder_name.data,
                            price=price,
                            currency='USD')
                    except Exception as e:
                        db.session.rollback()
                        flash(e.message, 'error')
                        return redirect(
                            url_for('conference.request_conference'))
                else:
                    default_conference_payment = ConferencePayment()
                db.session.add(default_conference_payment)
                conference.conference_payment = default_conference_payment
                db.session.add(conference)
                db.session.commit()
                # send email to admin
                send_email(current_app.config['CONF_SUPPORT'],
                           'New conference request',
                           'email/new_conference_request',
                           conference=conference)
                # send email to requester
                send_email(current_user.email, 'Conference request received',
                           'email/new_conference_request_requester',
                           conference=conference, user=current_user)
                add_event(current_user.full_name + ' upgrade the plan',
                          OrderedDict(
                              [('Message',
                                'Plan has been upgraded to ' + conference.type)]),
                          conference_id=conference.id,
                          type='conference_transaction_new')
                flash('You request has been sent to Conferency', 'success')
                return redirect(url_for('conference.request_conference'))
            else:
                flash(form.errors, 'error')
        return render_template(
            'conference/conference_request_form.html',
            type=type,
            form=form,
            publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY'],
            price=professional_addon.price)
    else:
        abort(404)


@conference.route('/add', methods=['GET', 'POST'])
@login_required
def add_conference():
    """Add new conference."""
    abort(404)
    # deprecated
    form = ConferenceForm()
    with open(os.path.join(APP_STATIC, 'json/subjects.json')) as f:
        choices = [(value, value) for value in json.load(f)]
    form.subjects.choices = choices
    form.process(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            # convert list to string
            form.subjects.data = '; '.join(form.subjects.data)
            website = form.website_url.data.replace('http://', '').replace('https://', '')
            conference = Conference(name=form.conference_name.data,
                                    short_name=form.short_name.data,
                                    website=website,
                                    address=form.address.data,
                                    city=form.city.data,
                                    state=form.state.data,
                                    country=form.country.data,
                                    start_date=form.start.data,
                                    end_date=form.end.data,
                                    info=form.info.data,
                                    subjects=form.subjects.data,
                                    tags=form.tags.data,
                                    requester_id=current_user.id,
                                    featured=form.featured.data)
            # default_track = Track(name='Default Track')
            # conference.tracks.append(default_track)
            # db.session.add(default_track)
            # conference.configuration["website_type"] = form.website_type.data
            db.session.add(conference)
            db.session.commit()

            wordpress_create_site(conference)

            flash('Successfully add a new conference', 'success')
            return redirect(url_for('conference.all_conference'))
        else:
            flash('Validation failed', 'error')
            flash(form.errors, 'error')
    return render_template('conference/conference_add.html', form=form)


@conference.route('/all', methods=['GET', 'POST'])
@login_required
def all_conference():
    page = request.args.get('page', 1, type=int)
    keywords = request.args.get('keywords', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    empty_flag = False
    conf_id = request.args.get('conf_id', '')
    selected_conference = Conference.query.filter_by(id=conf_id).all()
    current_user.conferences.append(selected_conference)
    result_count = -1
    if keywords == '' and location == '' and start_date == '' and end_date == '':
        pagination = Conference.query.filter_by(status="Approved").order_by(
            Conference.start_date.desc()).paginate(
            page,
            per_page=15,
            error_out=False)
        conferences = pagination.items
        result_count = len(Conference.query.with_entities(
            Conference.id).filter_by(status="Approved").all())
    else:
        if start_date != '' and end_date != '':
            conferences_result_date = Conference.query.filter(and_(
                Conference.start_date >= start_date,
                Conference.end_date <= end_date))
        elif start_date == '' and end_date == '':
            conferences_result_date = Conference.query
        elif start_date == '':
            conferences_result_date = Conference.query.filter(
                Conference.end_date <= end_date)
        elif end_date == '':
            conferences_result_date = Conference.query.filter(
                Conference.start_date >= start_date)

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
                )).filter_by(
            status="Approved").order_by(Conference.start_date.desc())
        result_count = len(
            conferences_result.filter_by(status="Approved").all())
        if not result_count:
            pagination = Conference.query.filter_by(
                status="Approved").order_by(
                Conference.start_date.desc()).paginate(page,
                                                       per_page=15,
                                                       error_out=False)
            conferences = pagination.items
            result_count = len(
                Conference.query.filter_by(status="Approved").all())
            empty_flag = True
        else:
            pagination = conferences_result.paginate(page,
                                                     per_page=15,
                                                     error_out=False)
        conferences = pagination.items
        # return redirect()
    # else:
    #     abort(404)
    today = datetime.date.today()
    return render_template('conference/conference_all.html',
                           empty_flag=empty_flag, conferences=conferences,
                           result_count=result_count, pagination=pagination,
                           keywords=keywords,
                           location=location,
                           start_date=start_date,
                           today=today,
                           end_date=end_date)


# edit info of a conference
@conference.route('/edit/<int:conference_id>', methods=['GET', 'POST'])
@chair_required
def edit_conference(conference_id):
    """Edit conference. Deprecated."""
    abort(403)
    conference = Conference.query.get_or_404(conference_id)
    form = ConferenceEditForm(request.form)
    with open(os.path.join(APP_STATIC, 'json/subjects.json')) as f:
        choices = [(value, value) for value in json.load(f)]
    if form.validate_on_submit():
        # convert list to string
        form.subjects.data = ';'.join(form.subjects.data)
        form.website.data = form.website.data.replace(
            'http://', '').replace('https://', '')
        conference.name = form.conference_name.data
        conference.short_name = form.short_name.data
        conference.website = form.website.data
        conference.address = form.address.data
        conference.city = form.city.data
        conference.state = form.state.data
        conference.country = form.country.data
        conference.start_date = form.start.data
        conference.end_date = form.end.data
        conference.info = form.info.data
        conference.subjects = form.subjects.data
        conference.tags = form.tags.data
        conference.featured = form.featured.data
        db.session.add(conference)
        db.session.commit()
        flash('Successfully update the conference', 'success')
        return redirect(url_for('conference.all_conference'))
    form.conference_name.data = conference.name
    form.short_name.data = conference.short_name
    form.website.data = conference.website
    form.address.data = conference.address
    form.city.data = conference.city
    form.state.data = conference.state
    form.country.data = conference.country
    form.start.data = conference.start_date
    form.end.data = conference.end_date
    form.info.data = conference.info
    form.tags.data = conference.tags
    form.featured.data = conference.featured
    form.subjects.choices = choices
    form.subjects.default = conference.subjects.split(';')
    form.subjects.process(request.form)
    return render_template('conference/conference_edit.html', form=form)


# *****All Conferences Page*****
# @main.route('/conference/search/<keywords>')
@conference.route('/search')
@login_required
def conferences_search():
    page = request.args.get('page', 1, type=int)
    keywords = request.args.get('keywords', '')
    location = request.args.get('location', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    empty_flag = False
    result_count = -1
    if keywords == '' and location == '' and start_date == '' and end_date == '':
        pagination = Conference.query.with_entities(
            Conference.id,
            Conference.name,
            Conference.short_name,
            Conference.address,
            Conference.city,
            Conference.state,
            Conference.country,
            Conference.start_date,
            Conference.end_date).order_by(
            Conference.start_date.desc()).paginate(
            page,
            per_page=15,
            error_out=False)
        conferences = pagination.items
        result_count = len(Conference.query.with_entities(Conference.id).all())
    else:

        # keyword = request.args.get('keyword')
        # location = request.args.get('location')
        # start_date = request.args.get('start')
        # end_date = request.args.get('end')

        if start_date != '' and end_date != '':
            conferences_result_date = Conference.query.filter(and_(
                Conference.start_date >= start_date,
                Conference.end_date <= end_date))
        elif start_date == '' and end_date == '':
            conferences_result_date = Conference.query
        elif start_date == '':
            conferences_result_date = Conference.query.filter(
                Conference.end_date <= end_date)
        elif end_date == '':
            conferences_result_date = Conference.query.filter(
                Conference.start_date >= start_date)

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
                )).order_by(Conference.start_date.desc())

        result_count = len(conferences_result.all())
        if not result_count:
            pagination = Conference.query.with_entities(
                Conference.id, Conference.name, Conference.short_name,
                Conference.address, Conference.city, Conference.state,
                Conference.country, Conference.start_date,
                Conference.end_date).order_by(
                Conference.start_date.desc()).paginate(page,
                                                       per_page=15,
                                                       error_out=False)
            conferences = pagination.items
            result_count = len(
                Conference.query.with_entities(Conference.id).all())
            empty_flag = True
        else:
            pagination = conferences_result.paginate(page,
                                                     per_page=15,
                                                     error_out=False)
        conferences = pagination.items
    # else:
    #     abort(404)

    return render_template('conference/conferences_search.html',
                           empty_flag=empty_flag, conferences=conferences,
                           result_count=result_count, pagination=pagination,
                           keywords=keywords, location=location,
                           start_date=start_date, end_date=end_date)


# *****Conference Page*****
@conference.route('/<int:conference_id>')
@login_required
def conferences_detail(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template(
        'conference/conferences_detail.html', conference=conference)


# *****Conference submission*****
# chair has the access to all submission, track chair has access to all
# submission in the track add query for track chair
@conference.route('/<int:conference_id>/submission/withdrawn',
                  endpoint='conferences_submission_withdrawn')
@conference.route('/<int:conference_id>/submission/deleted',
                  endpoint='conferences_submission_deleted')
@conference.route('/<int:conference_id>/submission',
                  endpoint='conference_submission')
@permission_required(Permission.MANAGE_REVIEW)
def conference_submission(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if conference_id == 1:
        abort(403)
    if current_user.curr_conf_id != int(conference_id):
        current_user.set_conference_id(conference_id)
    # empty_flag = False

    endpoint = request.endpoint.split('.')[1]

    track_list = current_user.get_track_list(conference)
    all_papers = conference.papers.filter(
        Paper.track_id.in_(track_list)).all()
    number_papers = [
        len(filter(lambda paper: paper.status not in ['Withdrawn', 'Deleted'],
                   all_papers)),
        len(filter(lambda paper: paper.status == 'Withdrawn', all_papers)),
        len(filter(lambda paper: paper.status == 'Deleted', all_papers))]
    tracks = conference.tracks.filter(Track.id.in_(track_list)).all()
    return render_template('conference/conference_submissions_all.html',
                           endpoint=endpoint,
                           conference=conference,
                           tracks=tracks,
                           number_papers=number_papers,
                           pdf_url=current_app.config['PDF_URL'])


@conference.route('/<int:conference_id>/submission/add',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def conference_submission_add(conference_id):
    """Chair manually add papers."""
    conference = Conference.query.get_or_404(conference_id)
    if conference_id == 1:
        abort(403)
    # add submission type
    if conference.configuration.get('submission_types', False):
        setattr(PaperForm,
                'submission_type',
                SelectField('Submission type *',
                            coerce=str,
                            choices=[
                                (type, type) for type in
                                conference.configuration.get(
                                    'submission_types', ['']).split(',')]))
    form = PaperForm()
    track_list = current_user.get_track_list(conference)
    tracks = conference.tracks.filter(
        Track.status == True, Track.id.in_(track_list)).all()
    if len(tracks) == 1:
        form.track_id.choices = [(tracks[0].id, tracks[0].name)]
        hide_tracks = True
    else:
        form.track_id.choices = [
            (track.id, track.name) for track in tracks if not track.default]
        hide_tracks = False
    dynamic = WTFormsDynamicFields()
    dynamic.add_field('author_sendnotification', '', BooleanField)
    dynamic.add_field('author_email', 'Email *', StringField)
    dynamic.add_field('author_firstname', 'First Name *', StringField)
    dynamic.add_field('author_lastname', 'Last Name *', StringField)
    dynamic.add_field('author_organization', 'Organization *', StringField)
    dynamic.add_field('author_country', 'Country *', StringField)
    dynamic.add_field('author_website', 'Website', StringField)
    dynamic.add_validator('author_email', required,
                          message='This field is required')
    dynamic.add_validator('author_email', email,
                          message='This field is required')
    dynamic.add_validator('author_firstname', required,
                          message='This field is required')
    dynamic.add_validator('author_lastname', required,
                          message='This field is required')
    dynamic.add_validator('author_organization', required,
                          message='This field is required')
    dynamic.add_validator('author_country', required,
                          message='This field is required')
    for id, question in conference.submission_questions.items():
        if question['include'] is True and question.get(
                'deleted', False) is False:
            if question['ques_type'] != 1:
                dynamic.add_field(id, question['desc'], StringField)
            else:
                # handle multi select
                dynamic.add_field(id, question['desc'], SelectMultipleField,
                                  choices=[
                                  (option, option) for option in
                                  question['options']],
                                  coerce=str)
            if question['require']:
                dynamic.add_validator(
                    id, required, message='This field is required')
    if request.method == 'POST':
        form = dynamic.process(PaperForm, request.form)
        # get default track or non default default tracks
        if len(tracks) == 1:
            form.track_id.choices = [(tracks[0].id, tracks[0].name)]
        else:
            form.track_id.choices = [
                (track.id, track.name) for track in tracks if
                not track.default]
        if form.validate_on_submit():
            paper_file = UserDoc.query.filter(
                and_(UserDoc.id.in_(form.filename.data.split(',')[:-1]),
                     UserDoc.uploader_id == current_user.id)).all()
            # if paper_file is None:
            #     flash("Please add a file", 'error')
            #     return redirect(url_for('submission.add_submission'))
            if True:
                custom_question_answer = OrderedDict()
                for id, question in conference.submission_questions.items():
                    custom_question_answer[id] = {
                        'answer':
                        form.__dict__.get(id + '_1').data if
                        form.__dict__.get(id + '_1') else '',
                        'ques_type': question['ques_type'],
                        'desc': question['desc']
                    }
                # Create the paper object
                paper = Paper(filename=paper_file[0].filename if
                              paper_file else None,
                              uploader_id=current_user.id,
                              title=form.title.data,
                              abstract=form.abstract.data,
                              keywords=form.keywords.data,
                              comment=form.comment.data,
                              conference_id=conference.id,
                              track_id=form.track_id.data,
                              custom_question_answer=custom_question_answer)
                for doc in paper_file:
                    paper.files.append(doc)
                if conference.configuration.get('submission_types', False):
                    paper.submission_type = form.submission_type.data
                # Turn the dynamic form's data into a dict so we can iterate
                # over it easie
                form_dict = form.__dict__
                i = 1
                authors = []
                while form_dict.get("author_email_" + str(i)):
                    cur_email = form_dict.get("author_email_" + str(i)).data
                    send_email_flag = False
                    user = User.query.filter_by(email=cur_email).first()
                    if user and user.primary_id:
                        # add to primary account
                        user = user.primary_user
                    if user:
                        # check if user has reach maximum submissions
                        if conference.configuration.get(
                                'submission_limit'):
                            if not user.can_submit_paper(conference.id):
                                # delete paper object
                                db.session.delete(paper)
                                flash(user.full_name + ' has reached maximum \
                                      number of submissions', 'error')
                                return redirect(
                                    url_for(
                                        'conference.conference_submission_add',
                                        conference_id=conference_id))
                        # user already existed
                        paper.authors.append(user)
                        authors.append(user.full_name)
                    else:
                        # add new user if the author doesn't exsit in database
                        pwd = User.generate_pwd()
                        user = User(email=cur_email,
                                    password=pwd,
                                    first_name=form_dict.get(
                                        "author_firstname_" + str(i)).data,
                                    last_name=form_dict.get(
                                        "author_lastname_" + str(i)).data,
                                    country=form_dict.get(
                                        "author_country_" + str(i)).data,
                                    website=form_dict.get(
                                        "author_website_" + str(i)).data,
                                    organization=form_dict.get(
                                        "author_organization_" + str(i)).data,
                                    confirmed=True
                                    )
                        db.session.add(user)
                        db.session.commit()
                        paper.authors.append(user)
                        send_email_flag = True
                        authors.append(user.full_name)
                    author = Author(email=cur_email,
                                    user_id=user.id,
                                    first_name=form_dict.get(
                                        "author_firstname_" + str(i)).data,
                                    last_name=form_dict.get(
                                        "author_lastname_" + str(i)).data,
                                    country=form_dict.get(
                                        "author_country_" + str(i)).data,
                                    website=form_dict.get(
                                        "author_website_" + str(i)).data,
                                    organization=form_dict.get(
                                        "author_organization_" + str(i)).data)
                    paper.authors_list.append(author)
                    db.session.add(author)
                    if send_email_flag:
                        # new user
                        # join conference
                        user.join_conference(conference)
                        # send an email to inform the new user
                        if form_dict.get('author_sendnotification_' + str(i)):
                            send_email(cur_email,
                                       'A paper with you as an author has been \
                                       submitted',
                                       'email/new_account_coauthor',
                                       reply_to=current_user.email,
                                       user=user,
                                       title=form.title.data, password=pwd,
                                       conference=conference.name,
                                       paper_id=paper.id)
                            send_email_flag = False
                    else:
                        # check if joined conference
                        if not user.is_joined_conference(
                                conference):
                            user.join_conference(conference)
                        # send email to inform author
                        if form_dict.get('author_sendnotification_' + str(i)):
                            send_email(cur_email,
                                       'A paper with you as an author has been \
                                       submitted',
                                       'email/submit_notification',
                                       reply_to=current_user.email,
                                       user=user,
                                       title=form.title.data,
                                       conference=conference.name,
                                       paper_id=paper.id)
                    i += 1
                authors = ', '.join(authors)
                if conference.configuration.get(
                        'submissions_notification'):
                    # send email to inform the chair and track chairs.
                    cur_track = Track.query.get_or_404(form.track_id.data)
                    all_chairs = conference.chairs + \
                        cur_track.track_chairs
                    for chair in all_chairs:
                        send_email(chair.email,
                                   '[' +
                                   conference.short_name.upper() +
                                   '] ' + 'A paper has been received',
                                   'email/submit_notification_chair',
                                   reply_to=current_user.email,
                                   chair=chair, authors=authors,
                                   title=form.title.data,
                                   conference=conference.name)
                db.session.add(paper)
                db.session.commit()
                add_event(current_user.full_name +
                          '(' + str(current_user.id) + ')' +
                          ' submitted paper: (' + str(paper.id) + ') ' +
                          paper.title,
                          paper.to_json_log(),
                          conference_id=paper.conference_id,
                          paper_id=paper.id,
                          type='paper_new')

                flash("Upload Successful", 'success')
                return redirect(
                    url_for('paper.get_paper_info',
                            paper_id=paper.id,
                            re='all_submission'))
        else:
            flash(form.errors, 'error')
            return redirect(url_for('conference.conference_submission_add',
                                    conference_id=conference_id))
    return render_template('submission/submission_add.html',
                           form=form, user=current_user,
                           submission_closed=False,
                           endpoint='chair_submission',
                           conference=conference,
                           hide_tracks=hide_tracks,
                           pdf_url=current_app.config['PDF_URL'])


@conference.route('/<int:conference_id>/download/submission/withdrawn',
                  endpoint='conferences_submission_withdrawn_download')
@conference.route('/<int:conference_id>/download/submission/deleted',
                  endpoint='conferences_submission_deleted_download')
@conference.route('/<int:conference_id>/download/submission')
@permission_required(Permission.MANAGE_REVIEW)
def conferences_submission_download(conference_id):
    if conference_id == 1:
        abort(403)
    conference = Conference.query.get_or_404(conference_id)
    track_list = current_user.get_track_list(conference)
    endpoint = request.endpoint
    if 'withdrawn' in endpoint:
        papers = conference.papers.filter(
            Paper.status == 'Withdrawn',
            Paper.track_id.in_(track_list)).order_by(
                Paper.submitted_time.asc()).all()
        zip_name = conference.short_name + '_withdrawn.zip'
    elif 'deleted' in endpoint:
        papers = conference.papers.filter(
            Paper.status == 'Deleted',
            Paper.track_id.in_(track_list)).order_by(
                Paper.submitted_time.asc()).all()
        zip_name = conference.short_name + '_deleted.zip'
    else:
        papers = conference.papers.filter(
            Paper.status != 'Withdrawn', Paper.status != 'Deleted',
            Paper.track_id.in_(track_list)).all()
        zip_name = conference.short_name + '_normal.zip'

    file_path = []
    basedir = current_app.config['UPLOADED_PAPERS_DEST']
    if len(papers) == 0:
        flash('You have no file to download.', 'error')
        abort(403)
    else:
        # try:
        failure_times = 0
        if not os.path.exists(current_app.config['ZIP_URL']):
            os.makedirs(current_app.config['ZIP_URL'])
        for paper in papers:
            for file in paper.files:
                new_name = 'paper_{}_{}.{}'.format(
                    paper.id,
                    file.id,
                    file.filename.split('.')[-1])
                if len(track_list) > 1:
                    filename = os.path.join(
                        paper.track.name,
                        paper.status,
                        str(paper.id),
                        new_name)
                else:
                    filename = os.path.join(
                        paper.status,
                        str(paper.id),
                        new_name)
                file_path.append((basedir + file.filename, filename))
        import zipfile
        with zipfile.ZipFile(
                current_app.config['ZIP_URL'] + zip_name,
                'w', zipfile.ZIP_DEFLATED) as zip:
            for path, filename in file_path:
                try:
                    zip.write(path, arcname=filename)
                except Exception:
                    failure_times += 1

        if failure_times < len(papers):
            return send_file(
                current_app.config['ZIP_URL'] + zip_name,
                mimetype='application/x-zip-compressed',
                as_attachment=True)
        else:
            paper_names = []
            for paper in papers:
                paper_names.append('{}_{}'.format(paper.id, paper.title))
            return jsonify(
                message=(
                    'Failed to download submission, all files are missing. '
                    'Please contact us.'),
                missing=paper_names), 502
            # except Exception as e:
            #     return jsonify(message="Unexpected error."), 502


# *****Conference review*****

# chair has the access to all review, track chair has access to all review in the track
# add query for track chair


@conference.route('/<int:conference_id>/review')
@permission_required(Permission.MANAGE_REVIEW)
def conferences_review(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    track_num = len(conference.tracks.all())
    if conference_id == 1:
        abort(403)
    if current_user.curr_conf_id != int(conference_id):
        current_user.set_conference_id(conference_id)
    search_options = OrderedDict(
        [(1, "Title"), (2, "Author"), (3, "Abstract"), (4, "Keywords")])
    page = request.args.get('page', 1, type=int)
    search_keyword = request.args.get('search_keyword', '').strip()
    search_type = request.args.get('search_type', 0, type=int)
    empty_flag = False

    track_list = current_user.get_track_list(conference)
    base_query = conference.get_papers.filter(Paper.track_id.in_(track_list))

    if not search_keyword or search_type not in search_options:
        pagination = base_query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)

        if pagination.total < 20:
            pagination = base_query.order_by(Paper.id.asc()).paginate(
                page, per_page=20, error_out=False)
    else:
        if search_type == 1:
            search_query = base_query.filter(
                Paper.title.contains(search_keyword))
        elif search_type == 2:
            search_query = base_query.from_self().join(Paper.authors_list).filter(
                Author.full_name.contains(search_keyword))
        elif search_type == 3:
            search_query = base_query.filter(Paper.abstract.contains(search_keyword))
        elif search_type == 4:
            search_query = base_query.filter(Paper.keywords.contains(search_keyword))
        else:
            return redirect(url_for('conference.conferences_review', conference_id=conference_id))

        pagination = search_query.order_by(Paper.id.asc()).paginate(page, per_page=20, error_out=False)
        if not pagination.total:
            pagination = base_query.order_by(Paper.id.asc()).paginate(page, per_page=20, error_out=False)
            empty_flag = True

    all_reviews_papers = pagination.items

    return render_template('conference/conference_reviews_all.html',
                           all_reviews_papers=all_reviews_papers,
                           pagination=pagination,
                           conference_id=conference_id,
                           track_num=track_num,
                           empty_flag=empty_flag,
                           pdf_url=current_app.config['PDF_URL'],
                           search_options=search_options,
                           search_type=search_type,
                           search_keyword=search_keyword)


# *****Conference review assignment*****
@conference.route('/<int:conference_id>/review/assignment/manual')
@permission_required(Permission.MANAGE_REVIEW)
def conferences_assignment_manual(conference_id):
    if conference_id == 1:
        abort(403)
    conference = Conference.query.get_or_404(conference_id)
    page = request.args.get('page', 1, type=int)
    search_keyword = request.args.get('search_keyword', '').strip()
    search_condition = request.args.get('search_condition', '').strip()
    search_type = request.args.get('search_type', '').strip()
    empty_flag = False
    track_list = current_user.get_track_list(conference)
    base_query = conference.get_papers.filter(Paper.track_id.in_(track_list))
    if not search_keyword:
        if search_condition == 'missing-reviews':
            search_query = base_query.outerjoin(
                paper_reviewer,
                Paper.id == paper_reviewer.c.paper_id).outerjoin(
                Review, and_(Review.reviewer_id == paper_reviewer.c.user_id,
                             Paper.id == Review.paper_id)
                             ).filter(Review.id == None)
        elif search_condition == 'missing-assignments':
            search_query = base_query.filter(~Paper.reviewers.any())
        elif search_condition == 'completed-reviews':
            search_query = base_query.filter(Paper.reviews.any())
            # search_query = base_query.join(Paper.reviews).join(
            #     paper_reviewer).group_by(Paper.id).having(
            #     db.func.count_(distinct(
            #         paper_reviewer.c.user_id)) == db.func.count_(
            #         distinct(Review.reviewer_id)))
        else:
            search_query = base_query
        pagination = search_query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)
    else:
        if search_type == 'title':
            search_query = base_query.filter(
                Paper.title.contains(search_keyword))
        elif search_type == 'author':
            search_query = base_query.from_self().join(
                Paper.authors_list).filter(
                Author.full_name.contains(search_keyword))
        elif search_type == 'reviewer':
            search_query = base_query.from_self().join(Paper.reviewers).filter(
                User.full_name.contains(search_keyword))
        else:
            return redirect(url_for('conference.conferences_assignment_manual',
                                    conference_id=conference_id))
        if search_condition == 'missing-reviews':
            search_query = search_query.outerjoin(
                paper_reviewer,
                Paper.id == paper_reviewer.c.paper_id).outerjoin(
                Review, and_(Review.reviewer_id == paper_reviewer.c.user_id,
                             Paper.id == Review.paper_id)
                             ).filter(Review.id == None)
        elif search_condition == 'missing-assignments':
            search_query = search_query.filter(~Paper.reviewers.any())
        elif search_condition == 'completed-reviews':
            search_query.filter(~Paper.reviews.any())
            # search_query = search_query.join(Paper.reviews).join(
            #     paper_reviewer).group_by(Paper.id).having(
            #     db.func.count_(distinct(
            #         paper_reviewer.c.user_id)) == db.func.count_(
            #             distinct(Review.reviewer_id)))
        pagination = search_query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)
    if not pagination.total:
        pagination = base_query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)
        empty_flag = True
    all_papers = pagination.items
    return render_template('conference/conference_review_assignment.html',
                           all_papers=all_papers, pagination=pagination,
                           search_keyword=search_keyword,
                           conference=conference,
                           track_num=len(conference.get_tracks.all()),
                           empty_flag=empty_flag,
                           pdf_url=current_app.config['PDF_URL'],
                           search_type=search_type,
                           search_condition=search_condition)


@conference.route('/<int:conference_id>/review/assignment/import',
                  methods=['POST'])
@permission_required(Permission.MANAGE_REVIEW)
def import_review_assignment(conference_id):
    """Import excel."""
    def get_id(string_with_id):
        reg = re.search('\{(.*?)\}', string_with_id)
        if reg:
            try:
                return int(reg.group(1))
            except Exception:
                return None
        return None
    conference = Conference.query.get_or_404(conference_id)
    members_id_dict = conference.members_id_dict()
    error_list = []
    num_reviewers = len(request.get_array(field_name='file')[0]) - 3
    if num_reviewers < 1:
        error_list.append('1')
        return ', '.join(error_list), 400
    xls_review_assignments = request.get_array(field_name='file')[1:]
    for index, review_assignment in enumerate(xls_review_assignments):
        if len(review_assignment) < 3 + num_reviewers or \
                len(set(review_assignment[3:])) < len(review_assignment[3:]):
            # reviewers have duplicate items
            error_list.append(str(index + 1))
            continue
        paper = conference.get_paper_by_id(review_assignment[0])
        if paper:
            error_flag = False
            reviewers_list = list(map(get_id, review_assignment[3:]))
            # check if the review is in the conference
            authors_list = [author.id for author in paper.authors.all()]
            paper.reviewers = []
            if reviewers_list:
                paper.status = PaperStatus.UNDER_REVIEW
            for reviewer_id in reviewers_list:
                if reviewer_id in members_id_dict and not (
                        reviewer_id in authors_list):
                    reviewer = User.query.get(reviewer_id)
                    paper.reviewers.append(reviewer)
                else:
                    error_list.append(str(index + 1))
                    error_flag = True
                    continue
            if error_flag:
                continue
            db.session.add(paper)
    if len(error_list):
        return ', '.join(error_list), 400
    else:
        try:
            db.session.commit()
            return 'Success', 201
        except Exception:
            db.session.rollback()
            return 'Operation failed', 400


@conference.route('/<int:conference_id>/review/assignment/<int:paper_id>')
@permission_required(Permission.MANAGE_REVIEW)
def conferences_paper_review_assignment(conference_id, paper_id):
    """Assign reviewers for a paper."""
    paper = Paper.query.filter(Paper.id == paper_id,
                               Paper.conference_id == conference_id).first()
    if paper is None:
        abort(404)
    conference = paper.conference
    bidding_exist = PaperBidding.query.filter(
        Paper.conference_id == conference.id,
        PaperBidding.paper_id == Paper.id).first() is not None
    reviewers = [
        dict(value=usr.full_name,
             data=dict(id=usr.id,
                       name=usr.full_name,
                       reviewed_count=len(
                           usr.review_assignment_conference(conference)),
                       review_preference=paper.get_bid(usr) if bidding_exist
                       else None,
                       organization=usr.organization or '',
                       is_reviewer=usr.is_reviewer(paper),
                       email=usr.email)) for usr in conference.reviewers]
    reviewers_json = json.dumps(reviewers)

    return render_template(
        'conference/conference_review_assignment_paper.html',
        paper=paper,
        reviewers_json=reviewers_json,
        pdf_url=current_app.config['PDF_URL'])


@conference.route('/<int:conference_id>/review/assignment/automatic',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def automatic_assignment(conference_id):
    """Automatic review assignment."""
    form = AutomaticAssignmentForm()
    conference = Conference.query.get_or_404(conference_id)
    track_list = current_user.get_track_list(conference)
    papers = conference.get_papers.filter(
        Paper.track_id.in_(track_list)).all()
    reviewers = conference.reviewers
    form.reviewers.choices = [
        (str(reviewer.id),
         '{} <{}>'.format(
             reviewer.full_name,
             reviewer.organization.encode(
                 'utf-8') if reviewer.organization else '').decode(
                     'utf-8')) for reviewer in reviewers]
    form.reviewers.default = [str(reviewer.id) for reviewer in reviewers]
    form.process(request.form)
    if request.method == 'POST':
        reviewer_ids = request.json['reviewers']
        try:
            num_reviewers_paper = int(request.json.get('num_reviewers_paper'))
        except Exception:
            return 'Invalid value for Number of Reviewer Per Paper', 403
        if num_reviewers_paper * len(
            request.json['papers']) > len(
                reviewer_ids) * int(conference.configuration.get(
                    'max_paper', sys.maxsize)):
            return 'Not enough reviewers', 403
        reviewers_list = []
        for reviewer_id in reviewer_ids:
            reviewer = User.query.get(reviewer_id)
            if (reviewer and reviewer in reviewers):
                if len(reviewer.review_assignment_conference(
                    conference)) < int(conference.configuration.get(
                        'max_paper', sys.maxsize)):
                    reviewers_list.append(reviewer)
            else:
                return 'Invalid reviewer', 403
        error_list = []
        for paper_id in request.json['papers']:
            paper = conference.get_paper_by_id(paper_id)
            if paper not in papers:
                return 'Invalid paper id', 403
            else:
                fail_flag = False
                paper.reviewers = []
                shuffle(reviewers_list)
                temp_reviewers = reviewers_list[:num_reviewers_paper]
                for _reviewer in temp_reviewers:
                    if paper.check_review_conflict(
                            _reviewer,
                            check_author=True,
                            check_reviewer=True)[0]:
                        paper.reviewers.append(_reviewer)
                    else:
                        # swap _reviewer with last one in the list
                        index = reviewers_list.index(_reviewer)
                        reviewers_list[-1], reviewers_list[index] = reviewers_list[index], reviewers_list[-1]
                        # retry 5 times
                        i = 0
                        while i < 5:
                            _reviewer = sample(reviewers_list[:-1], 1)[0]
                            if paper.check_review_conflict(
                                    _reviewer,
                                    check_author=True,
                                    check_reviewer=True)[0]:
                                paper.reviewers.append(_reviewer)
                                break
                            else:
                                i += 1
                                if i == 5:
                                    fail_flag = True
                    if len(_reviewer.review_assignment_conference(
                        conference)) >= int(conference.configuration.get(
                            'max_paper', sys.maxsize)):
                        reviewers_list.remove(_reviewer)
                if not fail_flag:
                    paper.status = PaperStatus.UNDER_REVIEW
                    db.session.add(paper)
                else:
                    error_list.append(str(paper.id))
        try:
            db.session.commit()
            if len(error_list):
                return ', '.join(error_list), 207
            else:
                return 'Success', 201
        except Exception:
            return 'Operation failed', 400
    return render_template(
        'conference/conference_review_assignment_automatic.html',
        conference=conference,
        papers=papers,
        form=form)


# *****Conference review assignment*****
@conference.route('/<int:conference_id>/review/decision',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def conferences_decision_review(conference_id):
    """Review decision page."""
    if conference_id == 1:
        abort(403)
    conference = Conference.query.get_or_404(conference_id)
    if request.method == 'POST':
        paper_id = request.form.get('paper_id', -1)
        paper_status = request.form.get('paper_status')
        paper = Paper.query.get_or_404(paper_id)
        paper.status = paper_status
        db.session.add(paper)
        db.session.commit()
        return "Success", 200

    search_options = OrderedDict(
        [(1, "Title"), (2, "Author"), (3, "Reviewer")])
    search_keyword = request.args.get('search_keyword', '').strip()
    search_type = request.args.get('search_type', '').strip()
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    sort = request.args.get('sort', -1, type=int)
    empty_flag = False

    track_list = current_user.get_track_list(conference)
    base_query = conference.get_papers.filter(
        Paper.track_id.in_(track_list)).order_by(Paper.id)
    if request.args.get('operation', False) in ['download_csv',
                                                'download_txt',
                                                'download_csv_sum']:
        from ...utils.export import generate_csv_response, \
            generate_txt_response, strip_html
        columns = ['Paper ID', 'Title', 'Avg review score',
                   'Status', 'Author', 'Reviewer']
        if request.args.get('operation') != 'download_csv_sum':
            columns += ['Review Score', 'Review Confidence',
                        'Confidential Remarks',
                        'Review']
        rows = []
        for paper in base_query.all():
            row = {
                'Paper ID': paper.id,
                'Title': paper.title,
                'Avg review score':
                    paper.avg_score if paper.avg_score else 'N/A',
                # 'Missing reviews':
                # len([review_status for review_status in paper.reviews_status if
                #     review_status[0] is False]),
                'Status': paper.status
            }
            rows.append(row)
            if request.args.get('operation') != 'download_csv_sum':
                for author in paper.authors_list.all():
                    row = {
                        'Author': '{} ({})'.format(
                            author.full_name,
                            author.organization.encode('utf-8'))
                    }
                    rows.append(row)
            else:
                row['Author'] = ', '.join(
                    [author.full_name + ' (' + author.organization + ')'
                     for author in paper.authors_list])
            if request.args.get('operation') != 'download_csv_sum':
                for review in paper.reviews:
                    row = {
                        'Reviewer': review.reviewer.full_name + (
                            ' ({})'.format(review.reviewer.organization.encode('utf-8')) if
                            review.reviewer.organization else ''),
                        'Review Score': review.evaluation,
                        'Review Confidence': review.confidence,
                        'Confidential Remarks':
                            review.confidential_comments,
                        'Review':
                            strip_html(review.review_body)
                    }
                    for question in review.custom_question_answer.values():
                        if type(question['answer']) != unicode:
                            answer = ' '.join(question['answer'])
                            row.update({question['desc']: answer})
                        else:
                            row.update({question['desc']: question['answer']})
                        if question['desc'] not in columns:
                            columns.append(question['desc'])
                    rows.append(row)
            else:
                row['Reviewer'] = ', '.join(
                    [review.reviewer.full_name + (' ({})'.format(
                        review.reviewer.organization.encode('utf-8')) if review.reviewer.organization else '')
                     for review in paper.reviews])
        if request.args.get('operation', False) in ['download_csv',
                                                    'download_csv_sum']:
            try:
                response = generate_csv_response(
                    columns, rows,
                    conference.short_name + '_reviews_decision_' +
                    datetime.datetime.today().strftime('%Y-%m-%d'))
                return response
            except Exception as e:
                flash(e.message + '. Please contact custom service',
                      'error')
                return redirect(
                    url_for('conference.conferences_decision_review',
                            conference_id=conference_id))
        elif request.args.get('operation', False) == 'download_txt':
            try:
                response = generate_txt_response(
                    columns, rows,
                    conference.short_name + '_reviews_decision_' +
                    datetime.datetime.today().strftime('%Y-%m-%d'))
                return response
            except Exception as e:
                flash(e.message + '. Please contact custom service',
                      'error')
                return redirect(
                    url_for('conference.conferences_decision_review',
                            conference_id=conference_id))
    if search_keyword:
        if search_type == 'title':
            search_query = base_query.filter(
                Paper.title.contains(search_keyword))
        elif search_type == 'author':
            search_query = base_query.from_self().join(
                Paper.authors_list).filter(
                Author.full_name.contains(search_keyword))
        elif search_type == 'reviewer':
            search_query = base_query.from_self().join(Paper.reviewers).filter(
                User.full_name.contains(search_keyword))
        else:
            search_query = base_query
    else:
        search_query = base_query
    if status:
        search_query = search_query.filter(Paper.status == status)
    if sort == 0:
        search_query = search_query.order_by(Paper.id.asc())
    elif sort == 1:
        search_query = search_query.order_by(Paper.avg_score.desc())
    elif sort == 2:
        search_query = search_query.order_by(Paper.avg_score.asc())
    elif sort == 3:
        search_query = search_query.order_by(Paper.status.desc())
    pagination = search_query.paginate(page, per_page=20, error_out=False)
    if not pagination.total:
        pagination = base_query.order_by(Paper.id.asc()).paginate(
            page, per_page=20, error_out=False)
        empty_flag = True
    papers = pagination.items
    return render_template('conference/conference_review_decision.html',
                           papers=papers, pagination=pagination,
                           track_num=len(track_list), conference=conference,
                           empty_flag=empty_flag, search_type=search_type,
                           search_keyword=search_keyword,
                           search_options=search_options, sort=sort,
                           status=status,
                           pdf_url=current_app.config['PDF_URL'])


# *****Conference review assignment***
@conference.route('/<int:conference_id>/review_request', methods=['GET'])
@permission_required(Permission.MANAGE_REVIEW)
def review_request_list(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    page = request.args.get('page', 1, type=int)
    track_list = current_user.get_track_list(conference)
    pagination = DelegateReview.query.filter(
        DelegateReview.paper_id == Paper.id,
        Paper.track_id.in_(track_list),
        DelegateReview.status != 'Revoked').order_by(
        DelegateReview.timestamp.desc()).paginate(page,
                                                  per_page=20,
                                                  error_out=False)
    review_delegations = pagination.items
    return render_template('conference/conference_review_request.html',
                           review_delegations=review_delegations,
                           conference_id=conference_id,
                           pagination=pagination,
                           endpoint='chair_review_request')


# *****Configuration*****
# Data need to be prepared while deploying
# We also need to check whether there is data in the system, if not,
# create at this step
@conference.route('/<int:conference_id>/setting', methods=['GET', 'POST'])
@chair_required
def conferences_setting(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if current_user.curr_conf_id != conference.id:
        abort(403)
    form = ConferenceEditForm()
    # selected subjects
    for subject in conference.subjects.split(';'):
        form.subjects.default.append(subject)
    form.subjects.process(request.form)

    if request.method == 'POST':
        if form.validate_on_submit():
            # update conference setting
            conference.name = form.conference_name.data
            # conference.short_name = form.short_name.data.lower()
            conference.contact_email = form.contact_email.data
            conference.contact_phone = form.contact_phone.data
            conference.address = form.address.data
            conference.city = form.city.data
            conference.state = form.state.data
            conference.website = form.website_url.data
            conference.country = form.country.data
            conference.start_date = form.start.data
            conference.end_date = form.end.data
            conference.timezone = form.timezone.data
            conference.info = form.info.data
            conference.subjects = ';'.join(form.subjects.data)
            conference.tags = form.tags.data
            db.session.add(conference)
            db.session.commit()
            flash('Conference settings updated', 'success')
            return redirect(url_for('conference.conferences_setting',
                                    conference_id=conference.id))

        else:
            flash(form.errors, 'error')
    form.conference_name.data = conference.name
    form.short_name.data = conference.short_name
    form.address.data = conference.address
    form.city.data = conference.city
    form.state.data = conference.state
    form.country.data = conference.country
    form.website_url.data = conference.website
    form.contact_email.data = conference.contact_email
    form.contact_phone.data = conference.contact_phone
    form.timezone.data = conference.timezone
    form.start.data = conference.start_date
    form.end.data = conference.end_date
    form.tags.data = conference.tags
    form.info.data = conference.info
    return render_template('conference/conferences_setting.html', form=form,
                           conference=conference)


@conference.route('/<int:conference_id>/website')
@chair_required
def website_management(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_website_setting.html',
                           conference=conference)


# *****Conference notification*****
@conference.route('/<int:conference_id>/notify/<string:operation>',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def send_notification(conference_id, operation):
    conference = Conference.query.get_or_404(conference_id)
    form = NotificationForm(operation)
    track_list = current_user.get_track_list(conference)
    if operation == 'pc':
        # all members of the conference
        # email_receivers = conference.pcs
        email_receivers_status = []
        papers = conference.get_papers.filter(
            Paper.track_id.in_(track_list)).all()
        status_list = sorted(list(set(
            [status for paper in papers for status in paper.reviews_status])))
        # add pc without review assignment
        for pc in conference.pcs:
            if not pc.get_review_assignments.filter(
                    Paper.track_id.in_(track_list)).all():
                status_list += [(None, pc)]
        # still has bug
        for status in status_list:
            if status[0]:
                # reviewers who have submitted review
                if (False, status[1]) in status_list:
                    # if reviewer has outstanding review, remove (True, ...)
                    status_list.remove(status)
                    email_receivers_status.append(1)
                else:
                    email_receivers_status.append(0)
            elif status[0] is False:
                # (False, ...)
                if (True, status[1]) in status_list:
                    status_list.remove((True, status[1]))
                email_receivers_status.append(1)
            elif status[0] is None:
                # (None, ...)
                if (True, status[1]) in status_list:
                    status_list.remove(status)
                if (False, status[1]) in status_list:
                    status_list.remove(status)
                email_receivers_status.append(2)
        form.email_receivers.choices = [
            (str(status[1].id), status[1].first_name +
             ' ' + status[1].last_name) for status in status_list]
        form.process(request.form)
        if form.receiver_type.data == 'checkbox_other':
            template_name = 'review_other'
        elif form.receiver_type.data == 'checkbox_complete':
            template_name = 'review_complete'
        elif form.receiver_type.data == 'checkbox_missing':
            template_name = 'review_missing'
        else:
            template_name = 'review_all'
    elif operation == 'author':
        for additional_status in conference.configuration.get(
                'additional_status', '').split(','):
            if additional_status:
                form.status_select.choices.append(
                    tuple([additional_status, additional_status]))
        form.process(request.form)
        if form.status_select.data == 'Under Review':
            template_name = 'author_under_review'
        elif form.status_select.data == 'Rejected':
            template_name = 'author_rejected'
        elif form.status_select.data == 'Received':
            template_name = 'author_received'
        elif form.status_select.data != 'Accepted':
            template_name = form.status_select.data
        else:
            template_name = 'author_accepted'
        papers = conference.papers.filter(
            Paper.status == form.status_select.data,
            Paper.track_id.in_(track_list)).all()
        for paper in papers:
            form.paper_ids.choices.append(tuple([paper.id, paper.id]))
    elif operation == 'member':
        papers = conference.get_papers.filter(
            Paper.track_id.in_(track_list)).all()
        members = conference.members
        form.email_receivers.choices = [
            (str(member.id), member.first_name + ' ' + member.last_name + '<' +
             member.email + '>') for member in members]
        form.process(request.form)
        template_name = 'member'
    elif operation == 'session':
        sessions = conference.conference_schedule.get_sessions.all()
        speakers = []
        moderators = []
        discussants = []
        for session in sessions:
            speakers += [(speaker, 0) for speaker in session.speakers.all()]
            moderators += [
                (moderator, 1) for moderator in session.moderators.all()]
            discussants += [
                (discussant, 2) for paper_session in
                session.paper_sessions.all() for discussant in
                paper_session.discussants]
        receivers = list(set(speakers)) + list(set(moderators)) + \
            list(set(discussants))
        form.email_receivers.choices = [
            (str(receiver[0].id), receiver[0].full_name + '<' +
             receiver[0].email + '>') for receiver in receivers]
        form.process(request.form)
        if form.receiver_type.data == 'checkbox_all':
            template_name = 'session_all'
        elif form.receiver_type.data == 'checkbox_speakers':
            template_name = 'session_speakers'
        elif form.receiver_type.data == 'checkbox_moderators':
            template_name = 'session_moderators'
        elif form.receiver_type.data == 'checkbox_discussants':
            template_name = 'checkbox_discussants'
        else:
            template_name = 'session_all'
    else:
        abort(403)
    if request.method == 'POST':
        form.process(request.form)
        # update template
        template = conference.email_templates.filter_by(
            name=template_name).order_by(
            EmailTemplate.timestamp.desc()).first()
        if not template or (form.email_content.data != template.content) or (
                form.email_subject.data != template.subject):
            email_template = EmailTemplate(name=template_name,
                                           subject=form.email_subject.data,
                                           content=form.email_content.data,
                                           conference_id=conference_id,
                                           user_id=current_user.id)
            db.session.add(email_template)
            db.session.commit()
        # temp
        # app = current_app._get_current_object()
        if operation == 'author':
            if form.validate_on_submit():
                if not papers:
                    flash('No email was sent', 'info')
                else:
                    # temp
                    # authors = [paper.authors_list.all() for paper in papers]
                    # thr = Thread(target=send_emails_to_authors,
                    #              args=[app, conference, papers, authors,
                    #                    operation, form])
                    # thr.start()
                    for paper in papers:
                        if paper.id in form.paper_ids.data:
                            for author in paper.authors_list:
                                content = template_convert(
                                    form.email_content.data, operation, author)
                                send_email(author.email,
                                           form.email_subject.data,
                                           'email/notification_authors',
                                           reply_to=conference.contact_email,
                                           content=content,
                                           conference=conference, user=author)
                                add_event('Send email to ' + author.full_name,
                                          OrderedDict(
                                              [('Subject',
                                                form.email_subject.data),
                                               ('Content', content)]),
                                          conference_id=conference_id,
                                          type='notification_author')
                    flash('Successfully Send emails')
            else:
                flash(form.errors, 'error')
        elif operation == 'pc':
            if form.validate_on_submit():
                if not form.email_receivers.data:
                    flash('No receiver to send email to.')
                else:
                    for receiver_id in form.email_receivers.data:
                        receiver = User.query.get(receiver_id)
                        if receiver:
                            content = template_convert(form.email_content.data,
                                                       operation, receiver)
                            send_email(receiver.email, form.email_subject.data,
                                       'email/notification_reviewers',
                                       reply_to=conference.contact_email,
                                       content=content,
                                       conference=conference, user=receiver)
                            add_event('Send email to ' + receiver.full_name,
                                      OrderedDict(
                                          [('Subject',
                                            form.email_subject.data),
                                           ('Content', content)]),
                                      conference_id=conference_id,
                                      type='notification_pc')
                    flash('Successfully Send emails')
            else:
                flash(form.errors, 'error')
        elif operation == 'member':
            if form.validate_on_submit():
                if not form.email_receivers.data:
                    flash('No receiver to send email to.')
                else:
                    for receiver_id in form.email_receivers.data:
                        receiver = User.query.get(receiver_id)
                        if receiver:
                            content = template_convert(form.email_content.data,
                                                       operation, receiver)
                            send_email(receiver.email, form.email_subject.data,
                                       'email/notification_members',
                                       reply_to=conference.contact_email,
                                       content=content,
                                       conference=conference, user=receiver)
                            add_event('Send email to ' + receiver.full_name,
                                      OrderedDict(
                                          [('Subject',
                                            form.email_subject.data),
                                           ('Content', content)]),
                                      conference_id=conference_id,
                                      type='notification_member')
                    flash('Successfully Send emails')
            else:
                flash(form.errors, 'error')
        elif operation == 'session':
            if form.validate_on_submit():
                if not form.email_receivers.data:
                    flash('No receiver to send email to.')
                else:
                    for receiver_id in form.email_receivers.data:
                        receiver = User.query.get(receiver_id)
                        if receiver:
                            content = template_convert(
                                form.email_content.data,
                                operation, receiver,
                                send_to=form.receiver_type.data)
                            send_email(receiver.email, form.email_subject.data,
                                       'email/notification_reviewers',
                                       reply_to=conference.contact_email,
                                       content=content,
                                       conference=conference, user=receiver)
                            add_event('Send email to ' + receiver.full_name,
                                      OrderedDict(
                                          [('Subject',
                                            form.email_subject.data),
                                           ('Content', content)]),
                                      conference_id=conference_id,
                                      type='notification_session')
                    flash('Successfully Send emails')
            else:
                flash(form.errors, 'error')
        return redirect(url_for('conference.send_notification',
                                conference_id=conference_id,
                                operation=operation))
    template = conference.email_templates.filter_by(
        name=template_name).order_by(
        EmailTemplate.timestamp.desc()).first()
    if template:
        form.email_subject.data = template.subject
        form.email_content.data = template.content
    if operation == 'author':
        return render_template('conference/conference_notification.html',
                               form=form,
                               conference_id=conference.id,
                               operation=operation,
                               template_name=template_name)
    elif operation == 'pc':
        return render_template('conference/conference_notification.html',
                               form=form,
                               conference_id=conference.id,
                               status_list=status_list,
                               email_receivers_status=email_receivers_status,
                               operation=operation,
                               template_name=template_name)
    elif operation == 'member':
        return render_template('conference/conference_notification.html',
                               form=form,
                               conference_id=conference.id, members=members,
                               operation=operation,
                               template_name=template_name)
    elif operation == 'session':
        return render_template('conference/conference_notification.html',
                               form=form,
                               conference_id=conference.id,
                               receivers=receivers,
                               operation=operation,
                               template_name=template_name)


@conference.route('/<int:conference_id>/track_notify', methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REVIEW)
def send_track_notification(conference_id):
    """Sned track notification."""
    conference = Conference.query.get_or_404(conference_id)
    form = TrackNotificationForm()
    track_list = current_user.get_track_object_list(conference, False)
    track_id_list = []
    role_list = []
    form.track_list.choices = []
    form.email_receivers.choices = []
    for track in track_list:
        choices = set()
        for paper in track.papers.filter(Paper.status != 'Withdrawn').all():
            for author in paper.authors:
                choices.add(
                    (author.id, author.first_name + ' ' + author.last_name))
        form.email_receivers.choices += list(choices)
        track_id_list += [track.id] * len(choices)
        role_list += [0] * len(choices)
        for item in track.members:
            if item.role.name == 'Program Committee':
                form.email_receivers.choices += [
                    (item.member.id, item.member.full_name)]
                track_id_list += [track.id]
                role_list += [1]
        form.track_list.choices.append((track.id, track.name))
    form.process(request.form)
    if form.validate_on_submit():
        for user_id in form.email_receivers.data:
            user = User.query.get(user_id)
            if user:
                content = form.email_content.data.replace(
                    '*CONFERENCE_WEBSITE*', conference.website) \
                    .replace('*NAME*', user.full_name) \
                    .replace('*FIRST_NAME*', user.first_name) \
                    .replace('*LAST_NAME*', user.last_name)
                send_email(user.email, form.email_subject.data,
                           'email/notification_track',
                           reply_to=conference.contact_email,
                           content=content)
        flash('Successfully Send emails')
    return render_template('conference/conference_notification_track.html',
                           track_id_list=track_id_list, role_list=role_list,
                           form=form)


# *****Conference tracks*****
@conference.route('/<int:conference_id>/tracks')
@permission_required(Permission.MANAGE_REVIEW)
def tracks(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    tracks_lv1 = conference.tracks.filter(
        Track.status == True, Track.default == False,
        Track.parent_track_id == None).all()
    return render_template('conference/conference_tracks.html',
                           tracks_lv1=tracks_lv1, conference=conference,
                           endpoint='tracks')


@conference.route('/<int:conference_id>/tracks_role')
@permission_required(Permission.MANAGE_REVIEW)
def track_role(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_tracks.html',
                           conference=conference,
                           endpoint='track_role')


# *****Conference registration*****
@conference.route('/<int:conference_id>/set_registration', methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def set_registration(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_setting.html',
                           conference=conference)


@conference.route('/<int:conference_id>/regsitration/tickets', methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_tickets(conference_id):
    """Tickets page."""
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_tickets.html',
                           conference=conference,
                           endpoint='registration_tickets')


@conference.route('/<int:conference_id>/regsitration/promo_codes',
                  methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_promo_code(conference_id):
    """Promo code page."""
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_tickets.html',
                           conference=conference,
                           endpoint='registration_promo_code')


@conference.route('/<int:conference_id>/registration/products',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_products(conference_id):
    """Registration products."""
    conference = Conference.query.get_or_404(conference_id)
    if request.method == 'POST':
        if (not request.form.get('product_name')) or \
                int(request.form.get('product_inventory', -2)) < -1 or \
                float(request.form.get('product_price', 0)) < 0 or \
                request.form.get('product_currency') not in [
                'USD', 'CNY', 'EUR', 'GBP', 'JPY']:
            flash('Invalid value in the form', 'error')
            return redirect(url_for('conference.registration_products',
                                    conference_id=conference_id))
        if request.form.get('_method') == 'post':
            product = Product(name=request.form.get('product_name'),
                              inventory=int(request.form.get(
                                  'product_inventory')),
                              registration_id=conference.registration.id,
                              price=float(
                              request.form.get('product_price', 0)),
                              currency=request.form.get('product_currency'))
            db.session.add(product)
            # process product option
            i = 0
            while request.form.get('new_option_name_' + str(i)):
                product_option = ProductOption(option_name=request.form.get(
                    'new_option_name_' + str(i)),
                    option_price=float(request.form.get(
                        'new_option_price_' + str(i))),
                    product_name=request.form.get('product_name'))
                product.options.append(product_option)
                db.session.add(product_option)
                i += 1
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(e.message, 'error')
            flash('Success')
            return redirect(url_for('conference.registration_products',
                                    conference_id=conference_id))
        elif request.form.get('_method') == 'put':
            product = Product.query.get(request.form.get('product_id'))
            # update product
            product.name = request.form.get('product_name')
            product.price = request.form.get('product_price')
            product.inventory = int(request.form.get('product_inventory'))
            product.currency = request.form.get('product_currency')
            db.session.add(product)
            # product.options = [
            #     option for option in product.options.all() if option.default]
            default_option = product.options.filter_by(default=True).first()
            default_option.product_name = request.form.get('product_name')
            default_option.option_price = request.form.get('product_price')
            db.session.add(default_option)
            product.options.append(default_option)
            # update existing non default options
            for option_id in [option_id_string[12:] for option_id_string
                              in request.form.keys() if
                              option_id_string.startswith('option_name_')]:
                product_option = ProductOption.query.get(option_id)
                product_option.option_name = request.form.get(
                    'option_name_' + option_id)
                product_option.option_price = float(request.form.get(
                    'option_price_' + option_id))
                product_option.product_name = request.form.get('product_name')
                product.options.append(product_option)
                db.session.add(product_option)
            # add new options
            i = 0
            while request.form.get('new_option_name_' + str(i)):
                product_option = ProductOption(option_name=request.form.get(
                    'new_option_name_' + str(i)),
                    option_price=float(request.form.get(
                        'new_option_price_' + str(i))),
                    product_name=request.form.get('product_name'))
                product.options.append(product_option)
                db.session.add(product_option)
                i += 1
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                flash(e.message, 'error')
            return redirect(url_for('conference.registration_products',
                                    conference_id=conference_id))
    return render_template('conference/conference_registration_tickets.html',
                           conference=conference,
                           endpoint='registration_products')


@conference.route('/<int:conference_id>/payment_options',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_REGISTRATION)
def payment_options(conference_id):
    """Paytout for conference."""
    payout = Conference.query.get_or_404(conference_id).registration.payout
    form = PayoutForm()
    if form.validate_on_submit():
        payout.account_name = form.account_name.data
        payout.street_1 = form.address_1.data
        payout.street_1 = form.address_2.data
        payout.city = form.city.data
        payout.state = form.state.data
        payout.country = form.country.data
        payout.zipcode = form.zipcode.data
        payout.payment_method = form.payment_method.data
        if form.payment_method.data == 'Direct Deposit':
            payout.bank_name = form.bank_name.data
            payout.account_type = form.account_type.data
            payout.routing_number = form.routing_number.data
            payout.account_number = form.account_number.data
        db.session.add(payout)
        db.session.commit()
        flash('Payout information has been saved')
        if current_user.is_administrator():
            return redirect(url_for('admin.admin_conf_registration',
                                    conference_id=conference_id))
        else:
            return redirect(url_for('conference.payment_options',
                                    conference_id=conference_id))
    if payout:
        form.account_name.data = payout.account_name
        form.address_1.data = payout.street_1
        form.address_2.data = payout.street_1
        form.city.data = payout.city
        form.state.data = payout.state
        form.country.data = payout.country
        form.zipcode.data = payout.zipcode
        form.payment_method.data = payout.payment_method
        if payout.payment_method == 'Direct Deposit':
            form.bank_name.data = payout.bank_name
            form.account_type.data = payout.account_type
            form.routing_number.data = payout.routing_number
            form.account_number.data = payout.account_number
    return render_template('conference/conference_payment_options.html',
                           payout=payout, form=form,
                           endpoint='payment_options')


@conference.route('/<int:conference_id>/set_registration_form',
                  methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def set_registration_form(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_form.html',
                           conference=conference,
                           endpoint='set_registration_form')


@conference.route('/<int:conference_id>/add_registration_form_questions',
                  methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def add_registration_form_questions(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_form.html',
                           conference=conference,
                           endpoint='add_registration_form_questions')


@conference.route('/<int:conference_id>/registration', methods=['POST'])
def attendee_registration(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    form = RegistrationForm()
    # included questions in order form
    private_question = []

    for k, v in conference.registration.private_question.items():
        v['id'] = k
        private_question.append(v)
    questions = filter(
        lambda x: x.get('deleted', False) is False and x['include'] is True,
        conference.registration.configuration_setting['questions'] +
        private_question)

    # dynamic form for additional question
    dynamic = WTFormsDynamicFields()
    for question in questions:
        if question['ques_type'] != 1:
            dynamic.add_field(question['id'], question['desc'], StringField)
        else:
            # handle multi select
            dynamic.add_field(
                question['id'],
                question['desc'],
                SelectMultipleField,
                choices=[
                    (option, option) for option in question['options']],
                coerce=unicode)
        if question['require']:
            dynamic.add_validator(
                question['id'], required, message='This field is required')

    if request.method == 'POST':
        # import order dictionary
        from collections import OrderedDict
        # process the request form
        form = dynamic.process(RegistrationForm, request.form)
        form.tickets.choices = [
            (ticket_price.id, ticket_price.currency)
            for ticket in conference.registration.tickets if
            ticket.status == 'Normal' and
            check_date(ticket,
                       conference.timezone) for ticket_price in ticket.prices]
        form.products.choices = [
            (product_option.id, product_option.option_name)
            for product in conference.registration.products.all() if
            product.status == 'Normal' for
            product_option in product.options.all()]
        form.process(request.form)
        # get the ticket first for price
        ticket_price = TicketPrice.query.get_or_404(form.tickets.data)
        total = ticket_price.amount
        # add product price
        product_options = []
        if len(form.products.data):
            for option_id in form.products.data:
                product_option = ProductOption.query.get_or_404(option_id)
                # check currency
                if product_option.product.currency == ticket_price.currency:
                    product_options.append(product_option)
                    total += product_option.option_price
                else:
                    flash('Cannot process your order, please check the \
                    additional items you selected. We do not support payment \
                    in different currencies.', 'error')
                    return redirect(url_for('main.conf_registration',
                                            conf_name=conference.short_name))
        # promo code
        if form.promo_code.data:
            promo_code = conference.registration.promo_codes.filter(and_(
                PromoCode.id == form.promo_code.data,
                PromoCode.status == 'Active',
                PromoCode.start_date <= datetime.date.today(),
                PromoCode.end_date >= datetime.date.today())).first()
            if promo_code and promo_code.currency == ticket_price.currency:
                if promo_code.type == 'percentage':
                    total *= (100 - promo_code.value) / 100.0
                else:
                    total -= promo_code.value
                if total < 0:
                    # when total < 0, set it to 0
                    total = 0.0
        if form.validate_on_submit() or total == 0.0:
            # when total <= 0 payment info is empty
            form_dict = form.__dict__
            # get attendee's info
            attendee_info = OrderedDict([
                ('First Name', form.attendee_first_name.data),
                ('Last Name', form.attendee_last_name.data),
                ('Email', form.attendee_email.data),
                ('Affiliation', form.attendee_affiliation.data)
            ])
            # get attendee's answers
            for question in questions:
                attendee_info[question['id']] = form_dict.get(
                    question['id'] + '_1').data if form_dict.get(
                    question['id'] + '_1') else ""
            if total > 0:
                try:
                    customer_id = generate_customer(
                        email=form.attendee_email.data,
                        source=form.stripeToken.data,
                        name=form.attendee_first_name.data + ' ' +
                        form.attendee_last_name.data)
                    charge_id, balance_transaction_id = charge(
                        customer_id=customer_id,
                        amount=total,
                        description='Registration for ' +
                                    form.attendee_first_name.data + ' ' +
                                    form.attendee_last_name.data +
                                    ' (' + conference.name + ')',
                        currency=ticket_price.currency)
                    net, balance_transaction_amount = get_net(
                        balance_transaction_id)
                except Exception as e:
                    # print e.message
                    flash(e.message, 'error')
                    return redirect(url_for('main.conf_index',
                                            conf_name=conference.short_name))
            ticket_transaction = TicketTransaction(
                registration_id=conference.registration.id,
                status=TransactionStatus.COMPLETED,
                card_number=form.card_number.data,
                attendee_info=attendee_info,
                holder_name=form.holder_name.data,
                security_code=form.security_code.data,
                expiration_date=form.month.data + '/' + form.year.data,
                billing_street=form.street.data,
                billing_city=form.city.data,
                billing_state=form.state.data,
                billing_country=form.country.data,
                billing_zipcode=str(form.zipcode.data),
                subtotal=total)
            if total > 0:
                ticket_transaction.net = net
                ticket_transaction.balance_transaction_id = \
                    balance_transaction_id
                ticket_transaction.balance_transaction_amount = \
                    balance_transaction_amount
                ticket_transaction.charge_id = charge_id
            # check if the attendee is a user
            user = User.query.filter_by(email=form.attendee_email.data).first()
            if user:
                ticket_transaction.buyer_id = user.id
                # join the conference
                if not user.is_joined_conference(conference):
                    user.join_conference(conference, registered=True)
                else:
                    # register
                    user.register(conference)
            else:
                new_user = User(email=form.attendee_email.data,
                                password=User.generate_pwd(),
                                first_name=form.attendee_first_name.data,
                                last_name=form.attendee_last_name.data,
                                confirmed=True,
                                organization=form.attendee_affiliation.data,
                                location=form.city.data,
                                state=form.state.data,
                                country=form.country.data)
                db.session.add(new_user)
                # user joins the conference after registration
                # new account email is not sent
                new_user.join_conference(conference, registered=True)
                ticket_transaction.buyer = new_user
            db.session.add(ticket_transaction)
            db.session.commit()
            ticket_transaction.add_ticket(ticket_price, 1)
            for product_option in product_options:
                ticket_transaction.add_product_option(product_option, 1)
            if 'promo_code' in locals() and promo_code and \
                    promo_code.currency == ticket_price.currency:
                ticket_transaction.apply_promo_code(promo_code)
            # send email to the attendee
            conf_short_name = str(conference.short_name)
            attendee_name = str(form.attendee_first_name.data) + \
                ' ' + str(form.attendee_last_name.data)
            send_email(
                form.attendee_email.data,
                'Registration Confirmation for ' + conf_short_name.upper(),
                'email/transaction_receipt',
                reply_to=conference.contact_email,
                attendee_name=attendee_name,
                transaction=ticket_transaction,
                conference=conference)
            add_event(attendee_name + ' registered for the conference',
                      ticket_transaction.to_json_log(),
                      conference_id=conference_id,
                      type='conference_registration')
        else:
            # print form.errors
            flash(form.errors, 'error')
            return redirect(url_for('main.conf_index',
                                    conf_name=conference.short_name))
    return render_template(
        'conference/conference_registration_transaction_info.html',
        conference=conference,
        transaction=ticket_transaction,
        attendee_email=form.attendee_email.data,
        disable_preloader=True)


@conference.route(
    '/<int:conference_id>/transaction/<int:transaction_id>/invoice')
@login_required
def transaction_invoice(conference_id, transaction_id):
    """Check the invoice."""
    conference = Conference.query.get_or_404(conference_id)
    ticket_transaction = TicketTransaction.query.get_or_404(transaction_id)
    if ticket_transaction.registration.conference != conference:
        abort(403)
    if ticket_transaction.buyer_id != current_user.id:
        abort(403)
    total_price = [ticket_transaction.subtotal]
    if ticket_transaction.product_options:
        for product_option_sale in ticket_transaction.product_options.all():
            total_price[0] = total_price[0] + \
                             product_option_sale.product_option.option_price
    return render_template(
        'conference/conference_registration_invoice.html',
        conference=conference,
        transaction=ticket_transaction,
        disable_preloader=True,
        total_price=total_price)


@conference.route('/<int:conference_id>/registration_summary', methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_summary(conference_id):
    """Registration summery."""
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_registration_summary.html',
                           conference=conference)


@conference.route('/<int:conference_id>/registration_info_download')
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_info_download(conference_id):
    from ...utils.export import generate_csv_response
    conference = Conference.query.get_or_404(conference_id)
    private_question = []
    for k, v in conference.registration.private_question.items():
        v['id'] = k
        private_question.append(v)
    questions = [
        question
        for question in filter(
            lambda x: x.get('deleted', False) is False and x[
                'include'] is True and x.get('hide') is not True,
            conference.registration.configuration_setting['questions'] +
            private_question)]

    questions_title = [question['desc'] for question in questions]
    # get products list
    product_options = [product.options.filter_by(default=False).all() if len(
        product.options.all()) != 1 else product.options.filter_by(
        default=True).first() for product in
        conference.registration.products.all()]
    from compiler.ast import flatten
    product_options = flatten(product_options)

    csv_columns = ['Order date', 'Order status', 'Ticket type',
                   'Quantity', 'Total paid', 'First Name', 'Last Name',
                   'Email', 'Affiliation']
    csv_columns += questions_title
    csv_columns += [option.product_name + '(' + option.option_name + ')'
                    if option.option_name != 'Default' else option.product_name
                    for option in product_options]
    try:
        rows = []
        for ticket_transaction in conference.registration.ticket_transactions:
            row = {
                'Order date': str(
                    ticket_transaction.timestamp.strftime('%Y-%m-%d')),
                'Order status': ticket_transaction.status,
                'Ticket type': ticket_transaction.tickets[0].name,
                'Quantity': len(ticket_transaction.tickets),
                'Total paid':
                    str(ticket_transaction.subtotal) + ' ' +
                    ticket_transaction.currency,
                'First Name': ticket_transaction.attendee_info['First Name'],
                'Last Name': ticket_transaction.attendee_info['Last Name'],
                'Email': ticket_transaction.attendee_info['Email'],
                'Affiliation': ticket_transaction.attendee_info['Affiliation']
            }

            for question in questions:
                _id = question['id'] or question['desc']
                if isinstance(ticket_transaction.attendee_info.get(_id, ''),
                              list):
                    row[question['desc']] = ', '.join(
                        ticket_transaction.attendee_info.get(_id, ''))
                else:
                    row[question['desc']] = ticket_transaction.attendee_info.get(
                        _id, '')

            for option in product_options:
                bought_option = ticket_transaction.product_options.filter_by(
                    product_option_id=option.id).first()
                row[option.product_name + '(' + option.option_name + ')'
                    if option.option_name != 'Default' else option.product_name] = bought_option.quantity if bought_option else ""

            rows.append(row)
        response = generate_csv_response(
            csv_columns, rows,
            conference.short_name + '_' +
            datetime.datetime.today().strftime('%Y-%m-%d'))
    except Exception:
        flash('Encoding error', 'error')
        return redirect(url_for('conference.registration_recent_orders',
                                conference_id=conference_id))

    return response


@conference.route('/<int:conference_id>/custom_review_question',
                  endpoint='conference_review_question')
@conference.route('/<int:conference_id>/review_form')
@permission_required(Permission.MANAGE_REVIEW)
def conference_review_form(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template(
        'conference/conference_review_form.html',
        conference=conference,
        endpoint='review_setting' if request.endpoint == 'conference.conference_review_form' else 'custom_review_question')


@conference.route('/<int:conference_id>/review_setting')
@permission_required(Permission.MANAGE_REVIEW)
def conference_review_setting(conference_id):
    """Conference review setting."""
    conference = Conference.query.get_or_404(conference_id)
    if current_user.is_chair(conference):
        return render_template('conference/conference_review_setting.html',
                               conference=conference,
                               endpoint='chair_control')
    else:
        track_id = current_user.get_track_list(conference)[0]
        return redirect(url_for('conference.conference_track_review_setting',
                                conference_id=conference_id,
                                track_id=track_id))


@conference.route('/<int:conference_id>/track/<int:track_id>/review_setting')
@permission_required(Permission.MANAGE_REVIEW)
def conference_track_review_setting(conference_id, track_id):
    conference = Conference.query.get_or_404(conference_id)
    tracks = [
        (track.id, track.name) for track in current_user.get_track_object_list(
            conference, False)]
    track = conference.tracks.filter_by(id=track_id).first()
    if track:
        return render_template('conference/conference_review_setting.html',
                               conference=conference, tracks=tracks,
                               track=track, endpoint='track_chair_control')
    else:
        abort(404)


# *****Conference memebers pages*****
@conference.route('/<int:conference_id>/members')
@chair_required
def conferences_members(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if current_user.curr_conf_id == 1:
        abort(403)
    page = request.args.get('page', 1, type=int)
    search_options = OrderedDict(
        [(1, "Name"), (2, "Email"), (3, "Affiliation")])
    search_keyword = request.args.get('search_keyword', '').strip()
    search_type = request.args.get('search_type', 0, type=int)
    role = request.args.get('role', '')
    show_error_msg = False
    members_all = search_query = User.query.filter(
        Track.conference_id == conference_id,
        JoinTrack.track_id == Track.id,
        User.id == JoinTrack.user_id,
        Track.default == True)
    if search_keyword:
        if search_type == 1:
            search_query = search_query.filter(
                (User.full_name).contains(search_keyword))
        elif search_type == 2:

            search_query = search_query.filter(
                User.email.contains(search_keyword))
        elif search_type == 3:
            search_query = search_query.filter(
                User.organization.contains(search_keyword))
        else:
            search_query = search_query
            show_error_msg = True
    if role:
        if role == "chair":
            role_name = "Chair"
        elif role == "pc":
            role_name = "Program Committee"
        elif role == "author":
            role_name = "Author"
        else:
            role_name = False
            show_error_msg = True
        if role_name:
            search_query = search_query.filter(
                JoinTrack.role_id == Role.query.filter_by(
                    name=role_name).first().id)
    if len(search_query.all()) == 0:
        search_query = members_all
        show_error_msg = True
    pagination = search_query.order_by(User.last_name.asc()).paginate(
        page, per_page=20, error_out=False)
    members = [
        (member, member.get_conference_role(conference).name,
         member.has_role_in_track(conference)) for member in pagination.items]
    total = pagination.total
    return render_template('conference/conference_members.html',
                           members=members,
                           conference_id=conference.id,
                           show_error_msg=show_error_msg,
                           search_keyword=search_keyword,
                           search_options=search_options,
                           search_type=search_type,
                           role=role,
                           total=total,
                           pagination=pagination)


@conference.route('/<int:conference_id>/add_members', methods=['GET', 'POST'])
@chair_required
def conferences_add_members(conference_id):
    """Add members."""
    conference = Conference.query.get_or_404(conference_id)
    page = request.args.get('page', 1, type=int)
    if request.method == 'POST':
        import base64
        joined_members = []
        error_list = []
        refresh = False
        success_count = 0
        # add signle user
        if request.form['type'] == 'form':
            user = User.query.filter_by(email=request.form['email']).first()
            if user and user.primary_id:
                # add primary account
                user = user.primary_user
            if not user:
                user = User(first_name=request.form['first_name'],
                            last_name=request.form['last_name'],
                            email=request.form['email'],
                            organization=request.form['organization'],
                            location=request.form['location'],
                            state=request.form['state'],
                            country=request.form['country'],
                            website=request.form['website'],
                            about_me=request.form['about_me'],
                            confirmed=True)
                db.session.add(user)
                try:
                    db.session.commit()
                    joined_members.append(user)
                except Exception:
                    db.session.rollback()
                    error_list.append(request.form['email'])
                if request.form['avatar']:
                    data_url = request.form['avatar'].split(',')[-1]
                    imgdata = base64.b64decode(data_url)
                    path = os.path.join(
                        current_app.config['UPLOADED_AVATAR_DEST'],
                        str(user.id) + '.png')
                    with open(path, 'wb') as f:
                        try:
                            f.write(imgdata)
                        except Exception:
                            abort(400)
                    user.avatar = '/' + os.path.join('static',
                                                     'upload',
                                                     'avatar',
                                                     str(user.id) + '.png')
                    db.session.add(user)
                    try:
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
            if not user.is_joined_conference(conference):
                role = Role.query.filter_by(name=request.form['role']).first()
                user.join_conference(conference, role=role, manual_added=True)
                success_count += 1
                if request.form.get('send_notification') == 'on':
                    # send notification
                    if user.password_hash:
                        send_email(user.email,
                                   'You have been added to ' +
                                   conference.short_name.upper(),
                                   'email/new_account_add_member',
                                   reply_to=conference.contact_email,
                                   conference=conference,
                                   user=user,
                                   role=role,
                                   new_user=False)
                    else:
                        # generate new user pwd
                        pwd = User.generate_pwd()
                        user.password = pwd
                        send_email(user.email,
                                   'You have been added to ' +
                                   conference.short_name.upper(),
                                   'email/new_account_add_member',
                                   reply_to=conference.contact_email,
                                   conference=conference,
                                   user=user,
                                   role=role,
                                   new_user=True, password=pwd)
                        db.session.add(user)
                        db.session.commit()
                refresh = True
            else:
                joined_members.append(user)
            add_event('Add member: ' + '%s %s' % (user.first_name, user.last_name),
                      user.user_info_json(),
                      conference_id=conference_id,
                      type='add_member')
        elif request.form['type'] == 'excel':
            xls_members = request.get_array(field_name='file')[1:]
            i = 2
            email_regex = '^[_a-zA-Z0-9-]+(\.[_a-zA-Z0-9-]+)*@[a-zA-Z0-9-]+(\.\
                [a-zA-Z0-9-]+)*(\.[a-zA-Z]{2,4})$'
            for xls_member in xls_members:
                if any(xls_member):
                    if len(xls_member) != 10 or not xls_member[0] or \
                            not xls_member[1] or \
                            not re.match(email_regex, xls_member[2]) or \
                            not xls_member[3] or not xls_member[4] or \
                            not xls_member[7]:
                        error_list.append(str(i))
                i += 1
            if len(error_list):
                return ', '.join(error_list), 400
            for xls_member in xls_members:
                if any(xls_member):
                    user = User.query.filter_by(email=xls_member[2]).first()
                    if user and user.primary_id:
                        # add to primary account
                        user = user.primary_user
                    if not user:
                        user = User(first_name=xls_member[0],
                                    last_name=xls_member[1],
                                    email=xls_member[2],
                                    organization=xls_member[3],
                                    location=xls_member[5],
                                    state=xls_member[6],
                                    country=xls_member[7],
                                    website=xls_member[8],
                                    about_me=xls_member[9],
                                    confirmed=True)
                        db.session.add(user)
                    if not user.is_joined_conference(conference):
                        role = Role.query.filter_by(name=xls_member[4]).first()
                        user.join_conference(conference,
                                             role=role,
                                             manual_added=True)
                        refresh = True
                        success_count += 1
                        if user.password_hash:
                            pwd = User.generate_pwd()
                            user.password = pwd
                            db.session.add(user)
                            db.session.commit()
                    else:
                        joined_members.append(user)
                    add_event(
                        'Add member: ' + user.full_name,
                        user.user_info_json(),
                        conference_id=conference_id,
                        type='add_member')
            db.session.commit()
        else:
            role = Role.query.filter_by(name=request.form['role']).first()
            if not role:
                abort(403)
            else:
                email_regex = '^[_a-zA-Z0-9-]+(\.[_a-zA-Z0-9-]+)*@[a-zA-Z0-9-]+(\.\
                    [a-zA-Z0-9-]+)*(\.[a-zA-Z]{2,4})$'
                for member_info in request.form['member_info'].split('\n'):
                    member_info = member_info.split()
                    # convert email address
                    if len(member_info) == 3:
                        member_info[2] = member_info[2].lower()
                        user = User.query.filter_by(
                            email=member_info[2]).first()
                        if user and user.primary_id:
                            # add to primary account
                            user = user.primary_user
                        if not user:
                            if re.match(email_regex, member_info[2]):
                                user = User(email=member_info[2],
                                            first_name=member_info[0],
                                            last_name=member_info[1],
                                            confirmed=True)
                                db.session.add(user)
                                try:
                                    db.session.commit()
                                except Exception:
                                    db.session.rollback()
                            else:
                                error_list.append(member_info)
                                # next
                                continue
                        send_email_flag = True
                        if user.is_joined_conference(conference):
                            if role.permissions >= user.get_conference_role(
                                    conference).permissions:
                                user.update_conference_role(conference, role)
                            else:
                                send_email_flag = False
                            joined_members.append(user)
                        else:
                            user.join_conference(conference, role=role,
                                                 manual_added=True)
                            refresh = True
                            success_count += 1
                        add_event('Add member: ' + '%s %s' % (
                                user.first_name, user.last_name),
                                  user.user_info_json(),
                                  conference_id=conference_id,
                                  type='add_member')
                        if request.form.get('send_notification') == 'on' and \
                                send_email_flag:
                            if user.password_hash:
                                send_email(user.email,
                                           'You have been added to ' +
                                           conference.short_name.upper(),
                                           'email/new_account_add_member',
                                           reply_to=conference.contact_email,
                                           conference=conference,
                                           user=user,
                                           role=role,
                                           new_user=False)
                            else:
                                # send password to new user
                                pwd = User.generate_pwd()
                                user.password = pwd
                                db.session.add(user)
                                send_email(user.email,
                                           'You have been added to ' +
                                           conference.short_name.upper(),
                                           'email/new_account_add_member',
                                           reply_to=conference.contact_email,
                                           conference=conference,
                                           user=user,
                                           role=role,
                                           new_user=True, password=pwd)
                                db.session.commit()
        if len(joined_members) or len(error_list):
            result_json = {
                'joined_members': [
                    {
                        member.email: member.full_name
                    } for member in joined_members],
                'error_list': [
                    {
                        member[2]: member[0] + ' ' + member[1]
                    } for member in error_list],
                'refresh': refresh,
                'success_count': success_count
            }
            return jsonify(result_json), 201
        else:
            return jsonify({'success_count': success_count,
                            'refresh': refresh}), 201
    else:
        pagination = User.query.filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id == conference.tracks.filter_by(
                default=True).first().id,
            JoinTrack.manual_added == True).paginate(page,
                                                     per_page=20,
                                                     error_out=False)
        members = pagination.items
    return render_template('conference/conference_members_add.html',
                           conference=conference,
                           pagination=pagination,
                           members=members)


@conference.route('/<int:conference_id>/members/csv')
@chair_required
def member_info_download(conference_id):
    from ...utils.export import generate_csv_response
    conference = Conference.query.get_or_404(conference_id)
    if 1 in [current_user.curr_conf_id, conference_id]:
        abort(403)
    name = request.args.get('name', '')

    members_all = User.query.filter(
        and_(Track.conference_id == conference_id,
             JoinTrack.track_id == Track.id,
             User.id == JoinTrack.user_id))

    if name:
        try:
            first_name, last_name = name.split()
        except ValueError:
            first_name = name
            last_name = name

        query = members_all.filter(or_(User.first_name.contains(first_name),
                                       User.last_name.contains(last_name))) \
            .order_by(User.first_name.asc())
    else:
        query = members_all.order_by(User.last_name.asc())

    members = query.all()
    if len(members) == 0:
        members = members_all.order_by(User.last_name.asc()).all()

    csv_columns = ['Name', 'Email', 'Organization', 'Role', 'Track Role']

    try:
        rows = []
        for member in members:
            row = {'Name': member.first_name + " " + member.last_name,
                   'Email': member.email,
                   'Organization': member.organization,
                   'Role': member.get_conference_role(conference).name,
                   'Track Role': member.has_role_in_track(conference)}

            rows.append(row)
        response = generate_csv_response(
            csv_columns,
            rows,
            conference.short_name + '_members_' +
            datetime.datetime.today().strftime('%Y-%m-%d'))
    except Exception as e:
        flash(e.message, 'error')
        return redirect(url_for('conference.member_info_download',
                                conference_id=conference_id,
                                name=name))

    return response


@conference.route('/<int:conference_id>/track_members')
@permission_required((Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION))
def track_members(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    track_list = current_user.get_track_list(conference, False)
    tracks = [track.to_json() for track in conference.tracks.filter(
        Track.id.in_(track_list), Track.parent_track_id == None).all()]
    return render_template('conference/conference_track_members.html',
                           conference=conference,
                           tracks=tracks)


@conference.route('/<int:conference_id>/registration_recent_orders',
                  methods=['GET'])
@permission_required(Permission.MANAGE_REGISTRATION)
def registration_recent_orders(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    private_question = []

    for k, v in conference.registration.private_question.items():
        v['id'] = k
        private_question.append(v)

    return render_template(
        'conference/conference_registration_recent_orders.html',
        conference=conference,
        questions=conference.registration.configuration['questions'] +
        private_question)


# ***** invitation ****
@conference.route('/<int:conference_id>/track_invitations',
                  endpoint='track_send_invitations', methods=['GET', 'POST'])
@conference.route('/<int:conference_id>/conference_invitations',
                  methods=['GET', 'POST'])
@permission_required(Permission.MANAGE_INVITATION)
def send_invitations(conference_id):
    """Send invitations."""
    conference = Conference.query.get_or_404(conference_id)
    form = InvitationsForm()
    # update track selection, role selection
    if request.url_rule.rule == '/conference/<int:conference_id>/conference_invitations':
        # empty track id selection
        del form.track_id
        form.role.choices = [('Author', 'Author'),
                             ('Program Committee', 'Program Committee'),
                             ('Chair', 'Chair')]
        # include default track
        track_list = current_user.get_track_list(conference)
    else:
        # not include default track
        track_list = current_user.get_track_list(conference, False)
        form.track_id.choices = [
            (str(track.id), track.name) for track in
            conference.tracks.filter(Track.id.in_(track_list)).all()]
        form.role.choices = [
            ('Track Program Committee', 'Track Program Committee'),
            ('Track Chair', 'Track Chair')]
    form.process(request.form)
    if form.validate_on_submit():
        if form.invitee_with_name.data:
            valid_emails_default = form.validate_invitees_names_emails(
                conference)
        else:
            valid_emails_default = form.validate_invitees_emails(conference)
        subject = form.email_subject.data
        if form.role.data == 'Chair':
            template_name = 'invitation_chair'
        elif form.role.data == 'Program Committee':
            template_name = 'invitation_PC'
        elif form.role.data == 'Author':
            template_name = 'invitation_author'
        elif form.role.data == 'Track Chair':
            template_name = 'invitation_trackChair'
        elif form.role.data == 'Track Program Committee':
            template_name = 'invitation_trackPC'
        template = conference.email_templates.filter_by(
                user_id=current_user.id,
                name=template_name).order_by(
                EmailTemplate.timestamp.desc()).first()
        if not (template and template.content == form.email_content.data and
                template.subject == form.email_subject.data):
            template = EmailTemplate(name=template_name,
                                     subject=form.email_subject.data,
                                     content=form.email_content.data,
                                     conference_id=conference_id,
                                     user_id=current_user.id)
            try:
                db.session.add(template)
                db.session.commit()
            except Exception:
                db.session.rollback()
        if valid_emails_default:
            if request.url_rule.rule == '/conference/<int:conference_id>/conference_invitations':
                track_id = conference.tracks.filter_by(default=True).first().id
            else:
                track_id = form.track_id.data
            emails_default_errors_list = list(form.emails_default.errors)
            for invitee_info in valid_emails_default:
                if form.invitee_with_name.data:
                    email = invitee_info[2]
                    last_name = invitee_info[1]
                    first_name = invitee_info[0]
                else:
                    email = invitee_info
                    last_name = ''
                    first_name = ''
                if not (check_name(first_name) and check_name(last_name)):
                    emails_default_errors_list.append(
                        first_name + ' ' + last_name + ' is invalid.')
                else:
                    content = form.email_content.data.replace(
                        '*CONFERENCE_WEBSITE*', conference.website) \
                        .replace('*FIRST_NAME*',
                                 first_name if first_name else 'member') \
                        .replace('*LAST_NAME*', last_name) \
                        .replace('*NAME*',
                                 current_user.full_name) \
                        .replace('*CONFERENCE_SHORTNAME*',
                                 conference.short_name.upper()) \
                        .replace('*CONFERENCE_NAME*', conference.name) \
                        .replace('*CONTACT_EMAIL*', conference.contact_email) \
                        .replace('*TRACK_NAME*',
                                 conference.tracks.filter_by(
                                    id=track_id).first().name)
                    token = current_user.generate_email_invitation_token(
                        email, form.role.data, track_id)
                    if not Invitation.add_invitation(current_user.id, email,
                                                     first_name, last_name,
                                                     form.role.data,
                                                     conference_id,
                                                     track_id, token,
                                                     {'subject': subject,
                                                      'content': content}):
                        emails_default_errors_list.append(
                            email + u' cannot be invited.')
            form.emails_default.errors = tuple(emails_default_errors_list)
            if len(emails_default_errors_list):
                flash('Some invitation emails failed to send.')
            else:
                flash('Invitation emails sent.')
        else:
            flash('No invitation emails sent.')
    form.invitee_with_name.data = False
    invitations_count = [0, 0, 0]
    invitations = conference.invitations.filter(
        Invitation.track_id.in_(track_list)).all()
    for invitation in invitations:
        if invitation.invitee_status == 'Pending':
            invitations_count[0] += 1
        elif invitation.invitee_status == 'Joined':
            invitations_count[1] += 1
        elif invitation.invitee_status == 'Declined':
            invitations_count[2] += 1
    if form.role.data == 'None':
        if request.url_rule.rule == '/conference/<int:conference_id>/conference_invitations':
            template_name = 'invitation_author'
        else:
            template_name = 'invitation_trackPC'
    return render_template('conference/conference_invitations.html',
                           form=form,
                           conference=conference,
                           search_options={},
                           search_type=0,
                           invitations_count=invitations_count,
                           template_name=template_name,
                           endpoint='send_invitations' if request.url_rule.rule == '/conference/<int:conference_id>/conference_invitations' else 'track_send_invitations')


@conference.route('/<int:conference_id>/invitation_pending')
@conference.route('/<int:conference_id>/invitation_joined',
                  endpoint='invitation_joined')
@conference.route('/<int:conference_id>/invitation_declined',
                  endpoint='invitation_declined')
@chair_required
@conference.route('/<int:conference_id>/track_invitation_pending',
                  endpoint='track_invitation_pending')
@conference.route('/<int:conference_id>/track_invitation_joined',
                  endpoint='track_invitation_joined')
@conference.route('/<int:conference_id>/track_invitation_declined',
                  endpoint='track_invitation_declined')
@permission_required(Permission.MANAGE_INVITATION)
def invitation_pending(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    page = request.args.get('page', 1, type=int)
    search_keyword = request.args.get('search_keyword', "", type=str).strip()
    search_options = OrderedDict([(1, "Name"), (2, "Email")])
    search_type = request.args.get('search_type', 0, type=int)
    role = request.args.get('role', '')
    show_error_msg = False
    if 'track' in request.url_rule.rule:
        endpoint = 'track_'
        # include default track
        track_list = current_user.get_track_list(conference, False)
    else:
        endpoint = ''
        # not include default track
        track_list = current_user.get_track_list(conference, True)
    invitations_count = [0, 0, 0]
    for index, status in enumerate(['pending', 'joined', 'declined']):
        if status in request.url_rule.rule:
            invitations_without_order = conference.invitations.filter(
                Invitation.track_id.in_(track_list),
                Invitation.invitee_status == (
                    status[0].capitalize() + status[1:]))
            if search_type == 1:
                invitations_without_order = invitations_without_order.filter(
                    Invitation.invitee_full_name.contains(search_keyword)
                )
            elif search_type == 2:
                invitations_without_order = invitations_without_order.filter(
                    Invitation.invitee_email.contains(search_keyword)
                )
            elif search_type == 0:
                pass
            else:
                show_error_msg = True
            if role == "chair":
                role_name = "Chair"
            elif role == "pc":
                role_name = "Program Committee"
            elif role == "author":
                role_name = "Author"
            elif role != "":
                role_name = False
                show_error_msg = True
            else:
                role_name = False
            if role_name:
                invitations_without_order = invitations_without_order.filter(
                    Invitation.invitee_role == role_name)
            # add order
            if status == 'pending':
                pagination = invitations_without_order.order_by(
                    Invitation.invitation_time.desc()).paginate(
                        page,
                        per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
                        error_out=False)
            else:
                pagination = invitations_without_order.order_by(
                    Invitation.reaction_time.desc()).paginate(
                        page,
                        per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
                        error_out=False)
            invitations_count[index] += pagination.total
            endpoint += 'invitation_' + status
        else:
            found_invitations = conference.invitations.filter(
                Invitation.track_id.in_(track_list),
                Invitation.invitee_status == (status.capitalize()),
                Invitation.invitee_full_name.contains(search_keyword))
            if search_type == 1:
                found_invitations = found_invitations.filter(
                    Invitation.invitee_full_name.contains(search_keyword))
            elif search_type == 2:
                found_invitations = found_invitations.filter(
                    Invitation.invitee_email.contains(search_keyword))
            if role == "chair":
                role_name = "Chair"
            elif role == "pc":
                role_name = "Program Committee"
            elif role == "author":
                role_name = "Author"
            elif role != "":
                role_name = False
                show_error_msg = True
            else:
                role_name = False
            if role_name:
                found_invitations = found_invitations.filter(
                    Invitation.invitee_role == role_name)
            invitations_count[index] += len(found_invitations.order_by(
                Invitation.reaction_time.desc()).all())
    invitations = pagination.items
    return render_template('conference/conference_invitations.html',
                           invitations_count=invitations_count,
                           search_options=search_options,
                           search_type=search_type,
                           show_error_msg=show_error_msg,
                           invitations=invitations,
                           conference=conference,
                           endpoint=endpoint,
                           pagination=pagination,
                           search_keyword=search_keyword)


@conference.route('/<int:conference_id>/log')
@chair_required
def logs(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    page = request.args.get('page', 1, type=int)
    pagination = conference.event_logs.order_by(
        EventLog.timestamp.desc()).paginate(page,
                                            per_page=20,
                                            error_out=False)
    logs = pagination.items
    return render_template('conference/conference_logs.html', logs=logs,
                           pagination=pagination, conference_id=conference_id)


@conference.route('/<int:conference_id>/summary')
@chair_required
def conference_summary(conference_id):
    name_abbr = dict()
    with open(os.path.join(APP_STATIC, 'json/countries.json')) as f:
        for value in json.load(f):
            name_abbr[value["value"]] = value["data"]
    current_conf = current_user.curr_conf
    papers = current_conf.papers.all()
    summary = {
        'under_review_number': 0,
        'accepted_number': 0,
        'rejected_number': 0,
        'withdrawn_number': 0,
        'sum_of_reviews': 0,
        'sum_of_review_assignments': 0,
        'outstanding_reviews_number': 0,
        'outstanding_reviews_paper_number': 0,
        'papers_number': 0,
        'no_assignment_paper': 0,
        'organization_summary': dict(),
        'author_summary': dict(),
        'reviewer_summary': dict(),
        'registration_distribution': dict()
    }
    # find registration distribution
    for transaction in current_conf.registration.ticket_transactions.all():
        transaction_country = User.query.filter_by(
            id=transaction.buyer_id).first().country
        transaction_num = len(transaction.tickets.all())
        summary['registration_distribution'][transaction_country] = summary['registration_distribution'].get(
            transaction_country, 0)
        summary['registration_distribution'][
            transaction_country] += transaction_num

    # will be updated if support multiple review rounds
    for paper in papers:
        if paper.status == PaperStatus.WITHDRAWN:
            summary['withdrawn_number'] += 1
        else:
            if paper.status == PaperStatus.ACCEPTED:
                summary['accepted_number'] += 1
            elif paper.status == PaperStatus.REJECTED:
                summary['rejected_number'] += 1
            else:
                summary['under_review_number'] += 1
            submitted_review_number = len(paper.reviews.all())
            review_assignment_number = len(paper.reviewers.all())
            if review_assignment_number == 0:
                summary['no_assignment_paper'] += 1
            summary['sum_of_reviews'] += submitted_review_number
            summary['sum_of_review_assignments'] += review_assignment_number
            outstanding_review_number_of_paper = review_assignment_number - submitted_review_number
            if outstanding_review_number_of_paper > 0:
                summary['outstanding_reviews_paper_number'] += 1
                summary[
                    'outstanding_reviews_number'] += outstanding_review_number_of_paper
            for organization in paper.get_organizations:
                summary['organization_summary'][organization] = summary['organization_summary'].get(organization,
                                                                                                    list())
                summary['organization_summary'][organization].append(paper)
            for author in paper.authors_list:
                summary['author_summary'][author.first_name + ' ' + author.last_name] = summary['author_summary'].get(
                    (author.first_name + ' ' + author.last_name), list())
                summary['author_summary'][author.first_name +
                                          ' ' + author.last_name].append(paper)
            for reviewer in paper.reviewers.all():
                summary['reviewer_summary'][reviewer.first_name + ' ' + reviewer.last_name] = summary[
                    'reviewer_summary'].get((reviewer.first_name + ' ' + reviewer.last_name), [0, 0, 0])
                summary['reviewer_summary'][
                    reviewer.first_name + ' ' + reviewer.last_name][0] += 1
            for review in paper.reviews.all():
                summary['reviewer_summary'][
                    review.reviewer.first_name + ' ' + review.reviewer.last_name][1] += 1
                summary['reviewer_summary'][review.reviewer.first_name + ' ' + review.reviewer.last_name][
                    2] += review.confidence
    organization_summary = list()
    for organization, confs in summary['organization_summary'].items():
        organization_summary.append([len(confs), organization, confs])
    organization_summary.sort(reverse=True)
    author_summary = list()
    for author, confs in summary['author_summary'].items():
        author_summary.append([len(confs), author, confs])
    author_summary.sort(reverse=True)
    reviewer_summary = list()
    for reviewer, review_status in summary['reviewer_summary'].items():
        if review_status[1]:
            reviewer_summary.append(
                ([review_status[0],
                  review_status[1],
                  review_status[2] / review_status[1]],
                 reviewer))
        else:
            reviewer_summary.append(([review_status[0], 0, 'N/A'], reviewer))
    reviewer_summary.sort(reverse=True)
    summary['organization_summary'] = organization_summary
    summary['author_summary'] = author_summary
    summary['reviewer_summary'] = reviewer_summary
    summary['papers_number'] = len(papers)
    total_submissions = summary['papers_number']
    total_reviews = summary['sum_of_reviews']
    total_registration = sum(
        ticket.number_of_sold for ticket in
        current_conf.registration.tickets.all())
    conf_name = current_conf.short_name

    return render_template(
        'conference/conference_summary.html',
        total_submissions=total_submissions,
        total_reviews=total_reviews,
        current_conf=current_conf, conf_name=conf_name,
        total_registration=total_registration,
        papers=papers, summary=summary)


@conference.route('/<int:conference_id>/submission_setting/form_questions',
                  endpoint='conference_submission_form_questions')
@conference.route('/<int:conference_id>/submission_setting/form')
@permission_required(Permission.MANAGE_REVIEW)
def conference_submission_form(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template(
        'conference/conference_submissions_form.html',
        conference=conference,
        tab='form' if request.endpoint == 'conference.conference_submission_form' else 'question')


@conference.route('/<int:conference_id>/submission_setting')
@permission_required(Permission.MANAGE_REVIEW)
def conference_submission_setting(conference_id):
    """Submission settings."""
    conference = Conference.query.get_or_404(conference_id)
    if request.endpoint == 'conference.conference_submission_form':
        tab = 'form'
    elif request.endpoint == 'conference.conference_submission_setting':
        tab = 'configuration'
    else:
        tab = 'question'
    if current_user.is_chair(conference):
        return render_template(
            'conference/conference_submissions_setting.html',
            conference=conference,
            endpoint='chair_control',
            tab=tab)
    else:
        # first track id
        # track_id = current_user.get_track_list(conference, False)[0]
        return redirect(
            url_for('conference.conference_track_submission_setting',
                    conference_id=conference_id))


@conference.route('/<int:conference_id>/tracks/submission_setting')
@permission_required(Permission.MANAGE_REVIEW)
def conference_track_submission_setting(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    tracks = [(track.id, track.name)
              for track in current_user.get_track_object_list(conference, False)]
    if tracks:
        track = conference.tracks.filter_by(id=tracks[0][0]).first()
        if track:
            return render_template(
                'conference/conference_submissions_setting.html',
                conference=conference, tracks=tracks, track=track,
                endpoint='track_chair_control')
        else:
            abort(404)
    else:
        abort(404)


@conference.route('/<int:conference_id>/review_preferences')
@login_required
def paper_biddings(conference_id):
    page = request.args.get('page', 1, type=int)
    conference = Conference.query.get_or_404(conference_id)
    review_preference = current_user.get_review_preference(conference)
    pagination = None
    if conference.configuration.get('allow_paper_bidding'):
        if current_user.get_conference_role(conference).name == 'Program Committee':
            pagination = conference.get_papers.paginate(page, per_page=20,
                                                        error_out=False)
        else:
            track_list = current_user.get_track_list(conference)
            pagination = conference.get_papers.filter(
                Paper.track_id.in_(track_list)).paginate(page,
                                                         per_page=20,
                                                         error_out=False)
    return render_template('conference/conference_paper_bidding.html',
                           pagination=pagination, conference=conference,
                           review_preference=review_preference)


@conference.route('/<int:conference_id>/reports')
@chair_required
def reports(conference_id):
    # conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_reports.html',
                           conference_id=conference_id)


@conference.route('/<int:conference_id>/reports/<string:report>')
@conference.route('/<int:conference_id>/reports/<string:report>/download_csv',
                  endpoint='download_report')
@chair_required
def get_report(conference_id, report):
    if report in ['author', 'reviewer', 'paper']:
        conference = Conference.query.get_or_404(conference_id)
        if request.endpoint == 'conference.download_report':
            from ...utils.export import generate_csv_response, strip_html
            if report in ['reviewer', 'author']:
                columns = ['First Name', 'Last Name', 'Affiliation', 'Email',
                           'Country', 'Paper ID', 'Paper Title',
                           'Registration Status']
                if report == 'reviewer':
                    columns += ['Evaluation', 'Confidence', 'Review']
            elif report == 'paper':
                columns = ['ID', 'Title', 'Status', 'Abstract', 'Keywords',
                           'Submission Type', 'Track', 'Label']
                author_count = 0
            rows = []
            for paper in conference.get_papers.all():
                if report == 'author':
                    for author in paper.authors_list:
                        row = {
                            'First Name': author.first_name,
                            'Last Name': author.last_name,
                            'Affiliation': author.organization,
                            'Email': author.email,
                            'Country': author.country,
                            'Paper ID': paper.id,
                            'Paper Title': paper.title,
                            'Registration Status': 'Yes' if
                            conference.is_user_registered(author.user_id) else
                            'No'
                        }
                        rows.append(row)
                elif report == 'reviewer':
                    for review in paper.reviews:
                        row = {
                            'First Name': review.reviewer.first_name,
                            'Last Name': review.reviewer.last_name,
                            'Affiliation': review.reviewer.organization,
                            'Email': review.reviewer.email,
                            'Country': review.reviewer.country,
                            'Paper ID': paper.id,
                            'Paper Title': paper.title,
                            'Registration Status': 'Yes' if
                            conference.is_user_registered(
                                review.reviewer.id) else 'No',
                            'Evaluation': review.evaluation,
                            'Confidence': review.confidence,
                            'Review': strip_html(review.review_body)
                        }
                        rows.append(row)
                elif report == 'paper':
                    row = {
                        'ID': paper.id,
                        'Title': paper.title,
                        'Status': paper.status,
                        'Abstract': paper.abstract,
                        'Keywords': paper.keywords,
                        'Submission Type': paper.submission_type if paper.submission_type else '',
                        'Track': paper.track.name if not paper.track.default else '',
                        'Label': paper.label if paper.label else ''
                    }
                    authors = paper.authors_list.all()
                    author_count = len(authors) if len(authors) > author_count else author_count
                    row.update(dict([('Author ' + str(index), author.full_name) for index, author in enumerate(authors, start=1)]))
                    rows.append(row)
            # add authors in columns
            if report == 'paper':
                columns += ['Author ' + str(i) for i in range(1, author_count + 1)]
            try:
                response = generate_csv_response(
                    columns, rows,
                    conference.short_name + '_' + report + '_' +
                    datetime.datetime.today().strftime('%Y-%m-%d'))
                return response
            except Exception:
                flash('Encoding error', 'error')
                return redirect(url_for('conference.get_report',
                                        conference_id=conference_id,
                                        report=report))
        # render pages
        else:
            display_option = request.args.get(
                'display_option', 'group_by_paper', type=str)
            if report == 'author':
                report_template = 'conference/conference_report_detail_author.html'
                report_name = 'Authors Summary'
            elif report == 'reviewer':
                report_template = 'conference/conference_report_detail_reviewer.html'
                report_name = 'Reviewers Summary'
            elif report == 'paper':
                report_template = 'conference/conference_report_detail_paper.html'
                report_name = 'Papers Summary'
            return render_template(report_template,
                                   conference=conference, report=report,
                                   report_name=report_name,
                                   display_option=display_option)
    else:
        abort(404)


@conference.route('/<int:conference_id>/schedule')
@chair_required
def schedule(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_schedule.html',
                           conference=conference)


@conference.route('/<int:conference_id>/embed_schedule')
def embed_schedule(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    sessions = conference.conference_schedule.get_sessions.all()
    venues = set([session.venue for session in sessions])
    return render_template('conference/embed/conference_schedule.html',
                           sessions=sessions,
                           conference=conference,
                           venues=venues)


@conference.route('/<int:conference_id>/proceedings')
@chair_required
def proceedings(conference_id):
    """Conference proceedings."""
    page = request.args.get('page', 1, type=int)
    checked_track_ids = request.args.getlist('tracks', type=int)
    checked_statuses = request.args.getlist('statuses', type=str)
    conference = Conference.query.get_or_404(conference_id)
    statuses = ['Accepted'] + \
               [additional_status for additional_status in
                conference.configuration.get(
                    'additional_status', '').split(',') if additional_status]
    if not checked_statuses:
        checked_statuses = statuses
    else:
        if not all(status in statuses for status in checked_statuses):
            checked_statuses = statuses
    tracks = conference.get_tracks.all()
    show_track = True
    if not tracks:
        # if only has default track
        tracks = conference.tracks.filter_by(default=True, status=True).all()
        show_track = False
    track_ids = [track.id for track in tracks]
    if not checked_track_ids:
        checked_track_ids = track_ids
    else:
        if not all(track_id in track_ids for track_id in checked_track_ids):
            checked_track_ids = track_ids
    pagination = conference.get_papers.filter(
        Paper.track_id.in_(checked_track_ids),
        Paper.status.in_(checked_statuses)).paginate(page,
                                                     per_page=20,
                                                     error_out=False)
    action = request.args.get('action', type=str)
    if action == 'select_all':
        for paper in pagination.query:
            paper.proceeding_included = True
            db.session.add(paper)
        db.session.commit()
    elif action == 'select_none':
        for paper in pagination.query:
            paper.proceeding_included = False
            db.session.add(paper)
        db.session.commit()
    # unselect some papers if selected tracks or statuses changed
    unselected_track_ids = [
        track_id for track_id in track_ids if track_id not in
        checked_track_ids]
    if unselected_track_ids:
        for paper in conference.get_papers.filter(
                Paper.track_id.in_(unselected_track_ids)).all():
            paper.proceeding_included = False
            db.session.add(paper)
    unselected_statuses = [
        status for status in statuses if status not in checked_statuses]
    if unselected_statuses:
        for paper in conference.get_papers.filter(
                Paper.status.in_(unselected_statuses)).all():
            paper.proceeding_included = False
            db.session.add(paper)
    db.session.commit()
    papers = pagination.items
    return render_template('conference/conference_proceedings.html',
                           conference=conference,
                           pagination=pagination,
                           page=page,
                           track_num=len(tracks),
                           papers=papers,
                           tracks=tracks,
                           checked_track_ids=checked_track_ids,
                           statuses=statuses,
                           checked_statuses=checked_statuses,
                           show_track=show_track,
                           pdf_url=current_app.config['PDF_URL'])


@conference.route('/<int:conference_id>/embed_proceedings')
def embed_proceedings(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if conference.configuration.get('use_proceeding_code'):
        return redirect(url_for('main.conf_proceedings',
                                conf_name=conference.short_name))
    papers = conference.get_papers.filter_by(
        proceeding_included=True).order_by(
        Paper.title.asc()).all()
    return render_template('conference/embed/conference_proceedings.html',
                           papers=papers)


@conference.route('/<int:conference_id>/upgrade', methods=['POST', 'GET'])
@chair_required
def payment(conference_id):
    """Accept payment for conference."""
    conference = Conference.query.get_or_404(conference_id)
    professional_addon = ConferenceAddon.query.filter_by(
        name='Professional Base Fee').first()
    if request.method == 'POST':
        promo_code = ConferencePromoCode.validate_promo_code(
            request.form.get('promo_code'))
        try:
            customer_id = generate_customer(
                email=current_user.email,
                source=request.form['stripeToken'],
                name=request.form['holder_name'])
            if promo_code:
                if promo_code.type == 'fixed_amount':
                    price = professional_addon.price - promo_code.value
                else:
                    price = professional_addon.price * (
                        1 - promo_code.value / 100)
                promo_code.usage += 1
                db.session.add(promo_code)
            else:
                price = professional_addon.price
            charge_id, balance_transaction_id = charge(
                customer_id=customer_id,
                amount=price,
                description=conference.short_name.upper() +
                ' upgrades to professional')
            conference.type = 'Professional'
            conference.conference_payment.card_info[
                request.form['card_number']] = {
                'card_number': request.form['card_number'],
                'holder_name': request.form['holder_name'],
                'security_code': request.form['security_code'],
                'month': request.form['exp'][:2],
                'year': request.form['exp'][3:]
            }
            conference.conference_payment.stripe_customer_id = customer_id
            conference.conference_payment.add_transaction(
                payer_id=current_user.id,
                charge_id=charge_id,
                balance_transaction_id=balance_transaction_id,
                addon_id=professional_addon.id,
                promo_code_id=promo_code.id if promo_code
                else None,
                amount=price)
            db.session.add(conference)
            db.session.commit()
            send_email(
                current_user.email,
                'Receipt for ' + conference.short_name.upper(),
                'email/conference_payment_receipt',
                conference=conference,
                title='Receipt for ' +
                conference.short_name.upper(),
                addons=[professional_addon],
                promo_code=promo_code,
                card_number=request.form['card_number'],
                holder_name=request.form['holder_name'],
                price=price,
                currency='USD')
            add_event(current_user.full_name + ' upgrade the plan',
                      OrderedDict(
                          [('Message',
                            'Plan has been upgraded to ' + conference.type)]),
                      conference_id=conference_id,
                      type='conference_transaction_new')
            flash('Thank you for supporting our product.')
            return redirect(url_for('conference.payment',
                                    conference_id=conference_id))
        except Exception as e:
            flash(e.message, 'error')
            db.session.rollback()
    return render_template(
        'conference/conference_payment.html',
        conference=conference,
        publishable_key=current_app.config['STRIPE_PUBLISHABLE_KEY'],
        professional=professional_addon)


@conference.route('/<int:conference_id>/billing_info')
@chair_required
def billing_info(conference_id):
    """Billing info for conference."""
    conference = Conference.query.get_or_404(conference_id)
    return render_template('conference/conference_billing_info.html',
                           conference=conference)
