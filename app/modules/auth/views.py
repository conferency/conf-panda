from flask import render_template, redirect, request, url_for, flash, \
    jsonify, abort
from flask.ext.login import login_user, logout_user, login_required, \
    current_user, session
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from . import auth
from ... import db
from ...models import User, Invitation, Conference, Track, DelegateReview, \
    InvitationStatus
from ...utils.macros import get_from_timeout_token
from ...utils.email_operation import send_email
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, \
    PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm, \
    InvitationRegistrationForm, TimeoutForm, InvitationDeclineForm, \
    ReviewRequestDeclineForm, MergeForm


# need optimization
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.endpoint[:5] != 'auth.' \
                and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/unconfirmed.html')


@auth.route('/invitation_login', methods=['GET', 'POST'],
            endpoint='invitation_login')
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Login function."""
    # get the conference id from url
    current_conf_id = request.args.get('conf', -1)
    invitation_token = request.args.get('invitation_token', False)
    delegation_id = request.args.get('delegation_id', -1)
    if invitation_token:
        data = User.email_invitation(invitation_token)
        if data:
            invitation_email, invitation_role, invitation_track_id = data
            try:
                check_invitation = Invitation.validate_invitation(
                    invitation_token, invitation_role, invitation_track_id)
            except Exception as e:
                flash(e.message, 'error')
                return redirect(url_for('auth.login'))
        else:
            flash('The invitation link is invalid or has expired.',
                  'error')
            return redirect(url_for('auth.login'))

    if not current_user.is_anonymous:
        # user have logged in
        if current_conf_id != -1:
            # login through conference page
            conference = Conference.query.get(current_conf_id)
            if not current_user.is_joined_conference(conference):
                current_user.join_conference(conference)
                flash('You joined ' + conference.short_name, 'info')
            current_user.set_conference_id(conference.id)
        elif invitation_token:
            if check_invitation.validate(current_user):
                check_invitation.accept_invitation(current_user)
                flash('Congratulations. You accepted the invitation.', 'info')
            else:
                flash('You are not the valid invitee of this invitation',
                      'error')
        elif delegation_id != -1:
            delegation = DelegateReview.query.get_or_404(delegation_id)
            if delegation.status == 'Pending':
                try:
                    delegation.accept_subreview(current_user.id)
                    flash('Thank you for accepting this reivew request')
                    return redirect(url_for('review.my_reviews'))
                except Exception as e:
                    flash(e.message, 'error')
            else:
                flash('This review request is not valid anymore', 'error')
        else:
            # login through index
            pass
            # flash('You have already logged in.', 'info')
        return redirect(url_for('main.dashboard'))
    form = LoginForm()
    next = request.args.get('next')
    conf_flag = False
    if current_conf_id != -1:
        conference = Conference.query.get(current_conf_id)
        if conference:
            # if conference exists
            conf_flag = True
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, False)  # form.remember_me.data)
            if user.is_administrator():
                return redirect(url_for('conf_admin.admin_dashboard'))
            if conf_flag:
                if not user.is_joined_conference(conference):
                    # join conference
                    user.join_conference(conference)
                # set curr_conf id
                user.set_conference_id(conference.id)
            if invitation_token:
                if check_invitation.validate(user):
                    check_invitation.accept_invitation(
                        user, request.form.get('note', ''))
                    flash('Congratulations. You accepted the invitation.',
                          'info')
                else:
                    flash('You are not the valid invitee of this invitation',
                          'error')
            elif delegation_id != -1:
                delegation = DelegateReview.query.get_or_404(delegation_id)
                if delegation.status == 'Pending':
                    try:
                        delegation.accept_subreview(user.id)
                        flash('Thank you for accepting this reivew request')
                        return redirect(url_for('review.my_reviews'))
                    except Exception as e:
                        flash(e.message, 'error')
                else:
                    flash('This review request is not valid anymore', 'error')
            # if user does't provide country and organization
            if user.country is None or user.organization is None or \
                    user.location is None:
                return redirect(url_for('main.edit_profile'))
            return redirect(request.args.get('next') or
                            url_for('main.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    if conf_flag:
        return render_template('auth/login.html', form=form,
                               conference=conference,
                               invitation=False, next=next)
    elif invitation_token:
        form.email.data = invitation_email
        return render_template('auth/login.html', form=form,
                               conference=check_invitation.conference,
                               track=check_invitation.track,
                               role=invitation_role,
                               token=invitation_token, invitation=True,
                               next=next)
    else:
        return render_template(
            'auth/login.html', form=form, invitation=False, next=next)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.pop('masqueraded', None)
    session.pop('origin', None)
    # flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    conf_flag = False
    current_conf_id = request.args.get('conf', -1)
    if current_conf_id != -1:
        conference = Conference.query.get(current_conf_id)
        if conference:
            conf_flag = True
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    first_name=form.firstname.data,
                    last_name=form.lastname.data,
                    password=form.password.data,
                    organization=form.organization.data,
                    country=form.country.data,
                    location=form.location.data,  # city
                    state=form.state.data)
        db.session.add(user)
        try:
            db.session.commit()
        except (IntegrityError, InvalidRequestError):
            db.session.rollback()
            flash('This email has been used, please log in', 'error')
            return redirect(url_for('auth.login'))
        if conf_flag:
            user.join_conference(conference)
            user.set_conference_id(conference.id)
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you.', 'info')
        # login_user(user, False)
        return redirect(url_for('auth.login'))
    # print(form.errors)
    if conf_flag:
        return render_template('auth/register.html', form=form,
                               conference=conference)
    else:
        return render_template('auth/register.html', form=form)


@auth.route('/invitationregister/<token>', methods=['GET', 'POST'])
def invitation_register(token):
    """Inviatation register."""
    form = InvitationRegistrationForm()
    data = User.email_invitation(token)
    if data:
        email = data[0]
        role = data[1]
        track_id = data[2]
        track = Track.query.filter_by(id=track_id, status=True).first()
    else:
        flash('The link is invalid or has expired.', 'error')
        return redirect(url_for('main.index'))
    check_invitation = Invitation.query.filter_by(token=token).first()
    if check_invitation is None:
        flash('Invitation link is invalid', 'error')
        return redirect(url_for('auth.login'))
    elif check_invitation.invitee_status == InvitationStatus.REVOKED:
        flash('This invitation has been revoked. If you didn\'t receive a \
              new invitation, please contact with the chair of the conference',
              'error')
        return redirect(url_for('auth.login'))
    elif check_invitation.invitee_status == InvitationStatus.JOINED:
        flash('Invitation has been redeemed. Log in to check the \
              conference.', 'info')
        return redirect(url_for('auth.login'))
    elif check_invitation.invitee_status != InvitationStatus.PENDING or \
            track is None:
        flash('Invitation has expired.', 'error')
        return redirect(url_for('auth.login'))
    else:
        user_registered = User.query.filter_by(
            email=check_invitation.invitee_email).first()
        if user_registered:
            return redirect(url_for('auth.invitation_login',
                                    invitation_token=token))

    conference = track.conference
    # assigned_role = Role.query.filter_by(name=role).first()
    if form.validate_on_submit():
        # if the chair send another invitation which user is filling the form,
        # the previous form is invalid
        if check_invitation.invitee_status == 'Revoked':
            flash('This invitation has been revoked. Please check out the \
                  latest invitation in your mail box', 'info')
            return redirect(url_for('auth.login'))
        new_user = User(email=email,
                        first_name=form.firstname.data,
                        last_name=form.lastname.data,
                        password=form.password.data,
                        organization=form.organization.data,
                        country=form.country.data,
                        location=form.location.data,
                        state=form.state.data,
                        confirmed=True)
        db.session.add(new_user)
        try:
            db.session.commit()
            login_user(new_user, False)
        except (IntegrityError, InvalidRequestError):
            flash('This email has been used, please log in to accept the \
                  invitation.', 'error')
            redirect(url_for('auth.invitation_register', token=token))
        check_invitation.accept_invitation(new_user, form.note.data)
        flash('Congratulations. Your account has been set up and the \
              notification email has sent to you.', 'info')
        return redirect(url_for('main.dashboard'))
    form.firstname.data = check_invitation.invitee_first_name if \
        check_invitation.invitee_first_name else ''
    form.lastname.data = check_invitation.invitee_last_name if \
        check_invitation.invitee_last_name else ''
    return render_template('auth/invitationregister.html',
                           form=form, email=email, role=role,
                           conference=conference,
                           track=track)


@auth.route('/invitationdecline/<token>', methods=['GET', 'POST'])
def invitation_decline(token):
    """Decline invitation."""
    form = InvitationDeclineForm()
    data = User.email_invitation(token)
    if data:
        email = data[0]
        role = data[1]
        track_id = data[2]
    else:
        flash('The link is invalid or has expired.', 'error')
        return redirect(url_for('main.index'))
    check_invitation = Invitation.query.filter_by(token=token).first()
    if check_invitation is None:
        flash('Invitation link is invalid', 'info')
        return redirect(url_for('auth.login'))
    elif check_invitation.invitee_status == InvitationStatus.REVOKED:
        flash('This invitation has been revoked. Please check out the latest \
              invitation in your mail box',
              'info')
        return redirect(url_for('auth.login'))
    elif check_invitation.invitee_status != InvitationStatus.PENDING:
        flash('Invitation has expired.', 'info')
        return redirect(url_for('auth.login'))
    track = Track.query.get(track_id)
    conference = track.conference
    if form.validate_on_submit():
        check_invitation.decline_invitation(form.note.data)
        flash('You have declined the invitation.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/invitationdecline.html',
                           form=form, email=email, role=role,
                           conference=conference,
                           track=track, check_invitation=check_invitation)


@auth.route('/review_request/<int:delegation_id>/<string:operation>',
            methods=['GET', 'POST'])
def review_request_operation(delegation_id, operation):
    delegation = DelegateReview.query.get_or_404(delegation_id)
    if delegation.status != 'Pending':
        abort(403)
    else:
        if operation == 'accept':
            return redirect(url_for('auth.login', delegation_id=delegation.id))
        elif operation == 'decline':
            form = ReviewRequestDeclineForm()
            if form.validate_on_submit():
                if delegation.delegatee.email != form.email.data:
                    flash('Wrong email address', 'error')
                    return redirect(
                        url_for('auth.review_request_operation',
                                delegation_id=delegation_id,
                                operation=operation))
                delegation.decline_subreview(form.note.data)
                flash('Thank you, delegator will receive your message.')
                return redirect(url_for('main.index'))
            return render_template(
                'auth/review_request_response.html', form=form)
        else:
            abort(403)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.dashboard'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!', 'success')
    else:
        flash('The confirmation link is invalid or has expired.', 'error')
    return redirect(url_for('main.dashboard'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you.', 'info')
    return redirect(url_for('main.dashboard'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash('Your password has been updated.', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid password.', 'error')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        flash('You have already logged in.', 'info')
        return redirect(url_for('main.dashboard'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
            flash('An email with instructions to reset your password \
                  has been sent to you.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('This email has not been registered yet.', 'error')
            return redirect(url_for('auth.password_reset_request'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        flash('You have already logged in.', 'error')
        return redirect(url_for('main.dashboard'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        try:
            user = User.reset_password(token, form.password.data)
            if user:
                login_user(user, False)
                flash('Your password has been updated.', 'success')
                return redirect(url_for('auth.login'))
        except Exception as e:
            flash(e.message, 'error')
            return redirect(url_for('main.dashboard'))
    return render_template('auth/new_password.html', form=form)


@auth.route('/change-email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'email/change_email',
                       user=current_user, token=token)
            flash('An email to confirm your new email '
                  'address has been sent to ' + new_email + '.', 'info')
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid email or password.', 'error')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change-email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash('Your email address has been updated.', 'success')
    else:
        flash('Invalid request.', 'error')
    return redirect(url_for('main.dashboard'))


@auth.route('/account', methods=['GET', 'POST'])
@auth.route('/account/settings', methods=['GET', 'POST'])
@login_required
def settings():
    pass_form = ChangePasswordForm(prefix='pass_form')
    chag_email_form = ChangeEmailForm(prefix='chag_email_form')
    merge_form = MergeForm(prefix='merge_form')
    # chag_setting_form = ChangeSettingForm(prefix='chag_setting_form')
    if request.form.get('pass_form-submit', None) == 'Change Password':
        if pass_form.validate_on_submit():
            if current_user.verify_password(pass_form.old_password.data):
                current_user.password = pass_form.password.data
                db.session.add(current_user)
                db.session.commit()
                flash('Your password has been updated.', 'success')
                return redirect(url_for('auth.settings'))
            else:
                flash('Invalid current password.', 'error')
    elif request.form.get(
            'chag_email_form-submit', None) == 'Change Email Address':
        if chag_email_form.validate_on_submit():
            if current_user.verify_password(chag_email_form.password.data):
                new_email = chag_email_form.email.data
                token = current_user.generate_email_change_token(new_email)
                send_email(new_email, 'Confirm your email address',
                           'email/change_email',
                           user=current_user, token=token)
                flash('An email with instructions to confirm your new email '
                      'address has been sent to you.', 'info')
                return redirect(url_for('auth.settings'))
            else:
                flash('Invalid current password.', 'error')
        else:
            flash('Invalid email.', 'error')
    elif request.form.get(
            'merge_form-submit', None) == 'Merge this account into your current account':
        if merge_form.validate_on_submit():
            user = User.query.filter_by(email=merge_form.email.data).first()
            if user == current_user:
                flash('Cannot merge ' + merge_form.email.data +
                      ' into this account', 'error')
                return redirect(url_for('auth.settings'))
            if current_user.primary_id is not None:
                flash(current_user.email + ' is not a primary account. You \
                      cannot merge another account into a non-primary account',
                      'error')
                return redirect(url_for('auth.settings'))
            if user.verify_password(merge_form.password.data):
                user.primary_id = current_user.id
                try:
                    db.session.add(user)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    flash(e.message, 'error')
                    return redirect(url_for('auth.settings'))
                # merge this user into current user
                send_email(current_user.email, 'Account merged',
                           'email/merge_account',
                           user_1=user, user_2=current_user)
                flash(user.email + ' has been merged into you account', 'info')
                return redirect(url_for('auth.settings'))
            else:
                flash('Invalid password.', 'error')
        else:
            flash(merge_form.errors, 'error')
    return render_template(
        'auth/settings.html', pass_form=pass_form,
        chag_email_form=chag_email_form,
        merge_form=merge_form)  # , chag_setting_form=chag_setting_form)


@auth.route('/login_api', methods=['POST'])
def login_api():
    email = request.form.get('user_email')
    user = User.query.filter_by(email=email).first()
    if user is not None and user.verify_password(request.form.get('password')):
        login_user(user)
        return jsonify(user.to_json()), 200
    else:
        return 'Invalid username or password.', 422


@auth.route('/timeout/<token>', methods=['GET', 'POST'])
def timeout(token):
    form = TimeoutForm()
    data = get_from_timeout_token(token)
    if not token and not current_user.is_anonymous:
        return redirect(data.get('redirect', url_for('main.dashboard')))
    form.email.data = data.get('email', '')
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user is not None and user.verify_password(form.password.data):
                login_user(user, False)
                flash('Welcome back.', 'success')
                if form.email.data == data.get('email'):
                    return redirect(data.get('redirect',
                                             url_for('main.dashboard')))
                else:
                    return redirect(url_for('main.dashboard'))
            flash('Invalid username or password.', 'error')
        else:
            flash('Please try again', 'error')
    return render_template('/auth/timeout.html',
                           token=token, form=form)


@auth.route('/switch_user/<int:user_id>')
@login_required
def switch_user(user_id):
    """Switch to primary user."""
    if current_user.primary_id == user_id:
        user = current_user.primary_user
    else:
        user = current_user.merged_users.filter_by(id=user_id).first()
    if user:
        login_user(user, False)
        flash('Switched to ' + user.email)
        return redirect(url_for('main.dashboard'))
    else:
        if request.args.get('current_url', False):
            flash('Cannot switch to an unassociated account', 'error')
            return redirect(request.args.get('current_url'))
        else:
            abort(403)
