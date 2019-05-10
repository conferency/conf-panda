# -*- coding: utf-8 -*-
"""Main functions."""

import os
import stripe
from flask import render_template, redirect, url_for, abort, flash, request, \
    current_app, json, session
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from sqlalchemy import or_
from collections import OrderedDict
from app.utils.event_log import add_event
from . import main
from .forms import EditProfileForm, RegistrationForm
from ... import APP_STATIC
from ... import db
from ...models import Permission, User, Paper, Conference, Ticket, \
    TicketTransaction, TransactionStatus, JoinTrack, PaperStatus, Invitation
from ...utils.decorators import permission_required
from ...utils.email_operation import send_email
from ...utils.macros import check_date
from ...utils.template_convert import template_convert


# Set cache control to private
@main.after_request
def add_header(response):
    response.cache_control.private = True
    response.cache_control.public = False
    return response


# @main.before_app_first_request
# def before_request():
#     current_user.set_conference_id(1)


# *****Landing Page*****
@main.route('/')
def index():
    # if the user is logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    else:
        return redirect(url_for('auth.login', next=request.args.get('next')))
    # return render_template('/site/main/index.html')


# *****Pricing Page*****
@main.route('/pricing')
def pricing():
    # if the user is logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('/site/main/pricing.html')


# *****Conf Landing Page*****
@main.route('/<conf_name>/preview', endpoint='index_preview')
@permission_required(Permission.MANAGE_REGISTRATION)
@main.route('/<conf_name>')
def conf_index(conf_name):
    """Deprecated."""
    conference = Conference.query.filter_by(
        short_name=conf_name.lower(), status='Approved').first()
    if conference:
        return redirect(url_for('auth.login', conf=conference.id))
    else:
        abort(404)
    # sigbps2016 index page
    # if conf_name == 'sigbps2016':
    #     return render_template('/site/conf/sigbps_conf_index.html',
    #                            conference=conference)
    # if conf_name == 'techust2016':
    #     return render_template('/site/conf/technion_conf_index.html',
    #                            conference=conference)
    if conference:
        # get country name dict
        name_dict = {}
        with open(os.path.join(APP_STATIC, 'json/countries.json')) as f:
            for value in json.load(f):
                name_dict[value['data']] = value['value']
        publishable_key = current_app.config['STRIPE_PUBLISHABLE_KEY']
        form = RegistrationForm()
        form.tickets.choices = [(ticket.id, ticket.name)
                                for ticket in conference.registration.tickets if ticket.status == 'Normal' and check_date(ticket, conference.timezone)]
        form.products.choices = [(product_option.id, product_option.option_name)
                                 for product in conference.registration.products.all() if product.status == 'Normal' for product_option in product.options.all() if not product_option.default]
        # fill user info
        if current_user.is_authenticated:  # the user is logged in
            form.attendee_first_name.data = current_user.first_name
            form.attendee_last_name.data = current_user.last_name
            form.attendee_email.data = current_user.email
            form.attendee_affiliation.data = current_user.organization
        # check if the request is preview
        if request.url_rule.rule == '/<conf_name>':
            preview_flag = False
        else:
            preview_flag = True
        private_questions = []
        for k, v in conference.registration.private_question.items():
            v['id'] = k
            private_questions.append(v)
        return render_template('/site/conf/conf_index.html', form=form,
                               private_questions=private_questions,
                               conference=conference,
                               publishable_key=publishable_key,
                               preview_flag=preview_flag,
                               name_dict=name_dict)
    else:
        flash('Conference not found', 'error')
        return redirect(url_for('main.index'))


@main.route('/<conf_name>/schedule')
def conf_schedule(conf_name):
    """Conference schedule."""
    conference = Conference.query.filter_by(
        short_name=conf_name.lower(), status='Approved').first()
    if conference:
        sessions = conference.conference_schedule.get_sessions.all()
        venues = set([session.venue for session in sessions])
        return render_template('/site/conf/conf_schedule.html',
                               sessions=sessions,
                               venues=venues,
                               conference=conference,
                               disable_preloader=True)
    else:
        flash('Conference not found', 'error')
        return redirect(url_for('main.index'))


@main.route('/<conf_name>/registration/preview',
            endpoint='registration_preview')
@permission_required(Permission.MANAGE_REGISTRATION)
@main.route('/<conf_name>/registration')
def conf_registration(conf_name):
    conference = Conference.query.filter_by(
        short_name=conf_name.lower(), status='Approved').first()
    if conference:
        publishable_key = current_app.config['STRIPE_PUBLISHABLE_KEY']
        form = RegistrationForm()
        form.tickets.choices = [
            (ticket.id, ticket.name)
            for ticket in conference.registration.tickets if ticket.status == 'Normal' and check_date(ticket, conference.timezone)]
        form.products.choices = [
            (product_option.id, product_option.option_name)
            for product in conference.registration.products.all() if product.status == 'Normal' for product_option in product.options.all() if not product_option.default]
        if current_user.is_authenticated:  # if the user is logged in
            form.attendee_first_name.data = current_user.first_name
            form.attendee_last_name.data = current_user.last_name
            form.attendee_email.data = current_user.email
            form.attendee_affiliation.data = current_user.organization
        if request.url_rule.rule == '/<conf_name>/registration':
            preview_flag = False
        else:
            preview_flag = True
        private_questions = []
        for k, v in conference.registration.private_question.items():
            v['id'] = k
            private_questions.append(v)
        return render_template('/site/conf/conf_registration.html',
                               private_questions=private_questions,
                               conference=conference, form=form,
                               publishable_key=publishable_key,
                               preview_flag=preview_flag,
                               disable_preloader=True)
    else:
        flash('Conference not found', 'error')
        return redirect(url_for('main.index'))


@main.route('/<conf_name>/proceedings', methods=['GET', 'POST'])
def conf_proceedings(conf_name):
    """Conference proceedings."""
    conference = Conference.query.filter_by(
        short_name=conf_name.lower(), status='Approved').first()
    if conference:
        if not conference.configuration.get('show_proceeding', False):
            return render_template('/site/conf/conf_proceedings.html',
                                   conference=conference,
                                   proceedings_unavailable=True,
                                   disable_preloader=True)
        # check if user has access to the proceedings
        proceeding_code = conference.configuration.get('proceeding_code',
                                                       False)
        # if (not proceeding_code) and \
        #     (not (current_user.is_authenticated and
        #           current_user.is_registered(conference))):
        #     # only registered users
        #     return render_template('/site/conf/conf_proceedings.html',
        #                            conference=conference,
        #                            only_registered=True,
        #                            disable_preloader=True)
        if not conference.configuration.get('use_proceeding_code'):
            papers = conference.get_papers.filter_by(
                proceeding_included=True).order_by(
                    Paper.title.asc()).all()
            return render_template('/site/conf/conf_proceedings.html',
                                   conference=conference,
                                   papers=papers,
                                   disable_preloader=True)
        elif (not (current_user.is_authenticated and
                   current_user.is_registered(conference))) and \
                (proceeding_code and
                    session.get('proceedings_access', False) !=
                    proceeding_code):
                # who has access code
                if request.method == 'POST':
                    if request.form.get('access_code') == proceeding_code:
                        session['proceedings_access'] = \
                            request.form.get('access_code')
                        return redirect(
                            url_for('main.conf_proceedings',
                                    conf_name=conference.short_name))
                    else:
                        flash('Invalid Access Code', 'error')
                return render_template('/site/conf/conf_proceedings.html',
                                       conference=conference,
                                       access_code_form=True,
                                       disable_preloader=True)
        elif (current_user.is_authenticated and
                current_user.is_registered(conference)) or \
                (proceeding_code and
                    session.get('proceedings_access', False) ==
                    proceeding_code):
                    papers = conference.get_papers.filter_by(
                        proceeding_included=True).order_by(
                            Paper.title.asc()).all()
                    return render_template('/site/conf/conf_proceedings.html',
                                           conference=conference,
                                           papers=papers,
                                           disable_preloader=True)
        else:
            papers = conference.get_papers.filter_by(
                proceeding_included=True).order_by(
                    Paper.title.asc()).all()
            return render_template('/site/conf/conf_proceedings.html',
                                   conference=conference,
                                   papers=papers,
                                   disable_preloader=True)
    else:
        flash('Conference not found', 'error')
        return redirect(url_for('main.index'))


@main.route('/preview', methods=['POST'])
def preview():
    email = request.form['email']
    send_email('support@conferency.com', 'Preview Code Request',
               'email/preview', email=email)
    return "Success", 200


@main.route('/landing')
def landing():
    # if the user is logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    # return render_template('index.html')
    return render_template('/site/landing_page.html')

# *****Dashboard*****


@main.route('/dashboard')
@login_required
def dashboard():
    current_conf = current_user.curr_conf
    total_confs = len(current_user.conferences) - 1  # Main conf does not count
    if current_user.curr_conf_is_main():
        total_submissions = len(current_user.get_papers.all())
        total_reviews = len(current_user.get_review_assignments.all())
        conf_name = "All Conferences"
    else:
        total_submissions = len(current_user.get_papers.filter_by(
            conference_id=current_user.curr_conf_id).all())
        total_reviews = len(current_user.get_review_assignments.filter_by(
            conference_id=current_user.curr_conf_id).all())
        conf_name = current_conf.short_name
        registration = current_conf.registration
        if current_user.is_chair(current_user.curr_conf):
            total_registration = sum(
                ticket.number_of_sold for ticket in registration.tickets.all())
            papers = current_conf.get_papers.all()
            summary = {
                'under_review_number': 0,
                'accepted_number': 0,
                'rejected_number': 0,
                'sum_of_reviews': 0,
                'sum_of_review_assignments': 0,
                'outstanding_reviews_number': 0,
                'outstanding_reviews_paper_number': 0,
                'papers_number': 0,
                'no_assignment_paper': 0,
                'additional_status_num': OrderedDict()
            }
            additional_status_list = current_conf.configuration.get(
                'additional_status', '').split(',')
            for additional_status in additional_status_list:
                summary['additional_status_num'][additional_status] = 0
            # will be updated if support multiple review rounds
            dashboard_log = []
            for paper in papers:
                if paper.status == PaperStatus.WITHDRAWN:
                    summary['withdrawn_number'] += 1
                else:
                    dashboard_log += [('paper', paper, paper.submitted_time)]
                    for review in paper.reviews.all():
                        dashboard_log += [('review', review, review.timestamp)]
                    if paper.status == PaperStatus.ACCEPTED:
                        summary['accepted_number'] += 1
                    elif paper.status == PaperStatus.REJECTED:
                        summary['rejected_number'] += 1
                    elif paper.status == PaperStatus.UNDER_REVIEW:
                        summary['under_review_number'] += 1
                    if paper.status in additional_status_list:
                        summary['additional_status_num'][paper.status] += 1
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
            summary['papers_number'] = len(papers)
            for transaction in registration.ticket_transactions.all():
                if transaction.status == TransactionStatus.COMPLETED:
                    dashboard_log += [('conference_registration', transaction, transaction.timestamp)]
            # only last 3 events
            if len(dashboard_log) > 3:
                dashboard_log = dashboard_log[-3:]
            return render_template('dashboard.html',
                                   total_submissions=total_submissions,
                                   total_reviews=total_reviews,
                                   current_conf=current_conf,
                                   conf_name=conf_name,
                                   total_confs=total_confs,
                                   total_registration=total_registration,
                                   dashboard_log=dashboard_log,
                                   summary=summary)
    return render_template('dashboard.html',
                           total_submissions=total_submissions,
                           total_reviews=total_reviews,
                           current_conf=current_conf,
                           conf_name=conf_name,
                           total_confs=total_confs)


# *****User Profile*****

# show user's profile
@main.route('/user/<int:id>')
@login_required
def user(id):
    user = User.query.filter_by(id=id).first_or_404()
    return render_template('profile.html', user=user,
                           endpoint='main.user',
                           current_user_or_not=user.id == current_user.id)


# edit user's profile
@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    # print(form)
    if request.method == 'POST':
        if form.validate_on_submit():
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            # current_user.location = form.location.data
            current_user.about_me = form.about_me.data
            current_user.organization = form.organization.data
            current_user.location = form.location.data
            current_user.state = form.state.data
            current_user.country = form.country.data
            current_user.website = form.website.data
            db.session.add(current_user)
            db.session.commit()
            flash('Profile updated.', 'success')
            return redirect(url_for('main.edit_profile'))
        else:
            flash(form.errors, 'error')
            return redirect(url_for('main.edit_profile'))
    form.first_name.data = current_user.first_name
    form.last_name.data = current_user.last_name
    form.location.data = current_user.location
    form.state.data = current_user.state
    form.about_me.data = current_user.about_me
    form.organization.data = current_user.organization
    form.country.data = current_user.country
    form.website.data = current_user.website

    if current_user.location and current_user.organization and current_user.country:
        hide_msg = True
    else:
        hide_msg = False
    return render_template('profile_edit.html', form=form, hide_msg=hide_msg, user=current_user)


# user's tickets
@main.route('/user/tickets')
@login_required
def show_tickets():
    return render_template('user_ticket_transactions.html')


# ***** record slow query *****
@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['CONF_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/invitations/decline/<token>', methods=['GET', 'POST'])
def decline(token):
    data = User.email_invitation(token)
    if data:
        email = data[0]
        role = data[1]
    else:
        flash('The link is invalid or has expired.', 'error')
        return redirect(url_for('main.index'))
    check_invitation = Invitation.query.filter_by(token=token).first()
    if not check_invitation.check_availablibity():
        # check for revoke
        if check_invitation.invitee_status == 'Revoked':
            flash(
                'This invitation has been revoked. Please check out the latest invitation in your mail box',
                'info')
        else:
            flash('The invitation has expired.', 'error')
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        check_invitation.invitee_status = 'Declined'
        db.session.add(check_invitation)
        db.session.commit()
        check_invitation.ping()
        flash('You have declined the invitation.', 'info')
        return redirect(url_for('main.index'))
    return render_template('decline.html', email=email, role=role)


# **** user connection ****

@main.route('/user')
@login_required
def user_search():
    page = request.args.get('page', 1, type=int)
    name = request.args.get('name', '')
    organization = request.args.get('organization', '')
    empty_flag = False

    total_user = 0

    admin_list = [i.user_id for i in JoinTrack.query.filter_by(
        track_id=1, role_id=1)]
    if name == '' and organization == '':
        users_result = User.query.filter(
            User.id.notin_(admin_list)).filter_by(confirmed=True)
        total_user = len(users_result.all())
        pagination = users_result.paginate(
            page,
            per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
            error_out=False)
    else:
        if name != '':
            try:
                first_name, last_name = name.split(' ')
            except ValueError:
                first_name = name
                last_name = name
        else:
            first_name = ''
            last_name = ''
        if organization != '':
            users_result = User.query.filter(User.organization.contains(organization)).filter(or_(User.first_name.contains(first_name),
                                                                                                  User.last_name.contains(last_name))).filter(User.id.notin_(admin_list)).filter_by(confirmed=True)
        else:
            users_result = User.query.filter(or_(User.first_name.contains(first_name),
                                                 User.last_name.contains(last_name))).filter(User.id.notin_(admin_list)).filter_by(confirmed=True)
        total_user = len(users_result.all())

        if not total_user:
            empty_flag = True
            users_result = User.query.filter(User.id.notin_(admin_list))
            total_user = len(users_result.all())
            pagination = users_result.paginate(
                page,
                per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
                error_out=False)
        else:
            pagination = users_result.paginate(
                page,
                per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
                error_out=False)

    users = pagination.items

    return render_template(
        'user_search.html', users=users, pagination=pagination, name=name,
        organization=organization, empty_flag=empty_flag,
        total_user=total_user)


@main.route('/followers/<int:id>')
@login_required
def followers(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('.blog'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<int:id>')
@login_required
def followed_by(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        flash('Invalid user.', 'error')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['CONF_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/follow/<int:id>', methods=['POST'])
@login_required
def follow(id):
    # print '###########'
    # print id
    user = User.query.filter_by(id=id).first()
    if user is None:
        # flash('Invalid user.', 'error')
        return 'Bad request(User is None)', 400
    if current_user.is_following(user):
        # flash('You are already following this user.', 'error')
        return 'Bad request', 400
    current_user.follow(user)
    # flash('You are now following %s.' % user.first_name, 'success')
    return "Success", 200


@main.route('/unfollow/<int:id>', methods=['POST'])
@login_required
def unfollow(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        # flash('Invalid user.', 'error')
        return 'Bad request(User is None)', 400
    if not current_user.is_following(user):
        # flash('You are not following this user.', 'error')
        return 'Bad request', 400
    current_user.unfollow(user)
    # flash('You are not following %s anymore.' % user.first_name, 'success')
    return "Success", 200


@main.route('/join/<int:conference_id>', methods=['POST'])
@login_required
def join(conference_id):
    conference = Conference.query.filter_by(id=conference_id).first()
    if conference is None:
        # flash('Invalid user.', 'error')
        return 'Bad request(conference is None)', 400
    if current_user.is_joined_conference(conference):
        return 'Bad request', 400
    current_user.join_conference(conference)
    return "Success", 200


@main.route('/quit/<int:id>', methods=['POST'])
@login_required
def quit(id):
    conference = Conference.query.filter_by(conference_id=id).first()
    if conference is None:
        # flash('Invalid user.', 'error')
        return 'Bad request(conference is None)', 400
    if not current_user.is_joined_conference(conference):
        # flash('You are not following this user.', 'error')
        return 'Bad request', 400
    current_user.quit(conference)
    # flash('You are not following %s anymore.' % user.first_name, 'success')
    return "Success", 200


@main.route('/setcurrconfid', methods=['POST'])
@login_required
def set_current_conference_id():
    conference_id = int(request.form.get('conference_id', -1))
    # next_endpoint = request.form.get('next')
    # print next_endpoint
    conference = Conference.query.filter_by(id=conference_id).first()
    if current_user.is_joined_conference(conference):
        current_user.set_conference_id(conference.id)
        # return url_for(next_endpoint, conference_id=conference_id), 200
        return 'Success', 200
    else:
        return 'Bad request', 400


# update the status of registration
@main.route('/setregistration', methods=['POST'])
@permission_required(Permission.MANAGE_CONFERENCE)
def set_conference_registration():
    conference = Conference.query.get_or_404(
        int(request.form.get('conference_id', -1)))
    registration = conference.registration
    # if current_user.can(Permission.MANAGE_CONFERENCE, conference):
    if request.form.get('registration_status') == 'true':
        if len(registration.tickets.all()):
            registration.status = True
        else:
            return 'Require ticket', 403
    else:
        registration.status = False
    db.session.add(registration)
    db.session.commit()
    return 'Success', 200


# hide ticket
@main.route('/setticketstatus', methods=['PUT'])
@permission_required(Permission.MANAGE_CONFERENCE)
def set_ticket_status():
    ticket = Ticket.query.get_or_404(int(request.form.get('ticket_id', -1)))
    ticket.status = request.form.get('ticket_status')
    db.session.add(ticket)
    db.session.commit()
    return 'Success', 200


@main.route('/getticketprice')
def get_ticket_price():
    ticket = Ticket.query.get_or_404(int(request.args.get('ticket_id', -1)))
    return str(ticket.price), 200


@main.route('/ticket_refund', methods=['PUT'])
@permission_required(Permission.MANAGE_CONFERENCE)
def ticket_refund():
    ticket_transaction = TicketTransaction.query.get_or_404(
        int(request.form.get('ticket_transaction_id', -1)))
    print(ticket_transaction)
    if ticket_transaction:
        try:
            ticket_transaction.refund_transaction()
            conference = ticket_transaction.registration.conference
            attendee_name = '{} {}'.format(
                ticket_transaction.attendee_info.get('First Name'),
                ticket_transaction.attendee_info.get('Last Name'))
            send_email(
                ticket_transaction.attendee_info.get('Email'),
                'Refund Confirmation for %s' % conference.short_name.upper(),
                'email/ticket_refund_confirmation',
                conference=conference,
                attendee_name=attendee_name,
                transaction=ticket_transaction)
            add_event(
                '%s issued refund for the conference ticket' % attendee_name,
                ticket_transaction.to_json_log(),
                conference_id=conference.id,
                type='conference_registration_refund')
            return 'Success', 200
        except Exception as e:
            print(e.message)
            return e.message, 403
    # if refund.status == 'succeeded':
    #     ticket_transaction.refund_id = refund.id
    #     ticket_transaction.update_status(TransactionStatus.REFUNDED)
    #     # need to be updated when transaction supports multiple tickets
    #     ticket = ticket_transaction.tickets[0]
    #     ticket.number_of_sold -= 1
    #     db.session.add(ticket)
    #     db.session.add(ticket_transaction)
    #     db.session.commit()
    #
    # else:
    #     return 'Refund failed', 501


@main.route('/send_ticket_receipt', methods=['POST'])
@permission_required(Permission.MANAGE_CONFERENCE)
def send_ticket_receipt():
    ticket_transaction = TicketTransaction.query.get_or_404(
        int(request.form.get('ticket_transaction_id', -1)))
    conf_short_name = str(
        ticket_transaction.registration.conference.short_name)
    send_email(ticket_transaction.attendee_info.get('Email'),
               'Registration Confirmation for ' + conf_short_name.upper(),
               'email/transaction_receipt',
               reply_to=ticket_transaction.registration.conference.contact_email,
               attendee_name=ticket_transaction.attendee_info.get('First Name') + ' ' + ticket_transaction.attendee_info.get('Last Name'),
               transaction=ticket_transaction,
               conference=ticket_transaction.registration.conference)
    return 'Success', 200


# sent email
# sent notification email to authors
@main.route('/sendemail', methods=['POST'])
@login_required
def send_email_test():
    """Deprecated."""
    abort(404)
    email_address = request.json['address']
    subject = request.json['subject']
    paper_id = request.json['paper_id']
    paper = Paper.query.get_or_404(paper_id)
    content = template_convert(
        request.json['content'], 'author', paper.authors_list.first())
    if send_email(email_address, subject, 'email/notification_authors',
                  reply_to=paper.conference.contact_email,
                  content=content,
                  conference=paper.conference, user=paper.authors.first()):
        return 'Success', 200
    else:
        return 'Bad request', 400


# sent notification email to assigned reviewer
@main.route('/sendemail2', methods=['POST'])
@login_required
def send_email_test2():
    """Deprecated."""
    abort(404)
    email_address = request.json['address']
    subject = request.json['subject']
    receiver_id = request.json['receiver_id']
    receiver = User.query.get_or_404(receiver_id)
    content = template_convert(request.json['content'], 'pc', receiver)
    if send_email(email_address, subject, 'email/notification_reviewers',
                  reply_to=current_user.curr_conf.contact_email,
                  content=content,
                  conference=current_user.curr_conf,
                  user=receiver):
        return 'Success', 200
    else:
        return 'Bad request', 400


@main.route('/sendemail3', methods=['POST'])
@login_required
def send_email_test3():
    email_address = request.json['address']
    subject = request.json['subject']
    content = request.json['content']
    content = content.replace('*NAME*', 'Full name placeholder')
    content = content.replace('*FIRST_NAME*', 'First name placeholder')
    content = content.replace('*LAST_NAME*', 'Last name placeholder')
    content = content.replace('*CONFERENCE_WEBSITE*',
                              current_user.curr_conf.website)
    if send_email(email_address, subject, 'email/notification_track',
                  reply_to=current_user.curr_conf.contact_email,
                  content=content):
        return 'Success', 200
    else:
        return 'Bad request', 400


# sent invitation email to test email
@main.route('/send_invitation_email', methods=['POST'])
@permission_required(Permission.MANAGE_INVITATION)
def send_invitation_email():
    email_address = request.json['address']
    subject = request.json['subject']
    content = request.json['content'].replace('*CONFERENCE_WEBSITE*',
                                              current_user.curr_conf.website).replace('*FIRST_NAME*',
                                                                                      'First name placeholder').replace('*LAST_NAME*',
                                                                                                                        'Last name placeholder').replace('*CONFERENCE_NAME*',
                                                                                                                                                         current_user.curr_conf.name).replace('*CONTACT_EMAIL*',
                                                                                                                                                                                              current_user.curr_conf.contact_email).replace('*TRACK_NAME*',
                                                                                                                                                                                                                                            'Track Name')
    if send_email(email_address, subject, 'email/custom_invitation',
                  reply_to=current_user.curr_conf.contact_email,
                  conference=current_user.curr_conf,
                  content=content, join_link='#', decline_link='#', test_email=True):
        return 'Success', 200
    else:
        return 'Bad request', 400


# resent invitation email
@main.route('/invitation_operation_email', methods=['PUT'])
@permission_required(Permission.MANAGE_INVITATION)
def invitation_operation_email():
    invitation = Invitation.query.filter_by(
        id=request.json.get('invitation_id'),
        invitee_status="Pending").first()
    if invitation:
        if request.json.get('operation') == 'resend':
            import datetime
            invitation.invitation_time = datetime.datetime.now()
            invitation.token = current_user.generate_email_invitation_token(
                invitation.invitee_email,
                invitation.invitee_role,
                invitation.track_id)
            db.session.add(invitation)
            db.session.commit()
            # print url_for('auth.invitation_register', token=invitation.token, _external=True)
            if send_email(invitation.invitee_email,
                          invitation.email_content['subject'],
                          'email/custom_invitation',
                          reply_to=invitation.conference.contact_email,
                          content=invitation.email_content['content'],
                          join_link=url_for(
                              'auth.invitation_register',
                              token=invitation.token, _external=True),
                          decline_link=url_for(
                              'auth.invitation_decline',
                              token=invitation.token, _external=True),
                          conference=invitation.conference, test_email=False):
                return 'Success', 200
        elif request.json.get('operation') == 'revoke':
            invitation.invitee_status = 'Revoke'
            db.session.add(invitation)
            db.session.commit()
            return 'Success', 200
    else:
        return 'Bad request', 400


# operation on invitation emails
@main.route('/all_invitation_email', methods=['POST'])
@permission_required(Permission.MANAGE_INVITATION)
def all_invitation_email():
    conference = Conference.query.get_or_404(request.json.get('conference_id'))
    for invitation in conference.invitations.filter_by(invitee_status='Pending').all():
        if request.json.get('commond') == 'resend':
            import datetime
            invitation.invitation_time = datetime.datetime.now()
            invitation.token = current_user.generate_email_invitation_token(invitation.invitee_email,
                                                                            invitation.invitee_role,
                                                                            invitation.track_id)
            if not send_email(invitation.invitee_email,
                              invitation.email_content['subject'],
                              'email/custom_invitation',
                              reply_to=conference.contact_email,
                              content=invitation.email_content['content'],
                              join_link=url_for('auth.invitation_register',
                                                token=invitation.token, _external=True),
                              decline_link=url_for('auth.invitation_decline',
                                                   token=invitation.token, _external=True),
                              conference=conference, test_email=False):
                return 'Bad request', 400
        elif request.json.get('commond') == 'revoke':
            invitation.invitee_status = 'Revoke'
        db.session.add(invitation)
        db.session.commit()
    return 'Success', 200


@main.route('/test_delgation_email', methods=['POST'])
@login_required
def test_delegation():
    paper = Paper.query.get_or_404(request.json['paper_id'])
    content = {}
    content['content'] = request.json['content'].replace(
        '*TITLE*', paper.title).replace(
        '*CONFERENCE_NAME*', paper.conference.name).replace(
        '*NAME*', request.json['first_name'] + ' ' +
        request.json['last_name']).replace(
        '*FIRST_NAME*', request.json['first_name']).replace(
        '*LAST_NAME*', request.json['last_name'])
    if send_email(request.json['address'], request.json['subject'],
                  'email/review_delegate_notification',
                  reply_to=current_user.curr_conf.contact_email,
                  content=content, test_email=True):
        return 'Success', 200
    else:
        return 'Bad request', 400

# shutdown the server during selenium testing


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/policy/<policy_name>')
def policies(policy_name):
    policy_pages = ['data', 'cookies', 'payment']
    if policy_name not in policy_pages:
        abort(404)
    else:
        if policy_name == 'data':
            return render_template('policy/data_policy.html')
        if policy_name == 'cookies':
            return render_template('policy/cookie_use.html')
        if policy_name == 'payment':
            return render_template('policy/payment_terms.html')


@main.route('/notifications')
@login_required
def notifications():
    """Notifications page."""
    page = request.args.get('page', 1, type=int)
    pagination = current_user.get_notifications.paginate(page, per_page=30,
                                                         error_out=False)
    notifications = pagination.items
    return render_template('Notifications.html', pagination=pagination,
                           notifications=notifications)

@main.route('/email_landing')
def email_landing():
    error_msg = request.args.get('error_msg', '')
    print(error_msg)
    """ Landing page for login-less email page. """
    return render_template('email_landing.html', error_msg=error_msg)
