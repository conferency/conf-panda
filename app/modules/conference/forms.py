from flask.ext.wtf import Form
from wtforms import TextAreaField, SubmitField, DateField, BooleanField, StringField, \
    IntegerField, DateTimeField, SelectField, SelectMultipleField, widgets, RadioField, \
    HiddenField
from wtforms.validators import Required, Length, Regexp, Email, Optional, DataRequired
from wtforms import ValidationError
from flask import url_for
from ...models import User
# Imports for the invitation form
from ...utils.macros import split_on_comma_and_trim, split_on_return
import time
import re
import os
import json
from ... import APP_STATIC
from ...utils.regex import name_validator


def process_website_url(value):
    if isinstance(value, unicode):
        return value.replace(
            'http://', '').replace('https://', '')
    return value


class ConferenceForm(Form):
    conference_name = StringField('Conference name', validators=[
        Required(), Length(1, 128)])
    short_name = StringField('Conference short name', validators=[
        Required(), Regexp('^[a-zA-Z_]{1,10}\d{4}$',
                           message="Incorrect Format"), Length(1, 64)])
    # website_type = StringField('Website Type',
    #                            validators=[Required(), Length(1, 128)])
    website_url = StringField(
        'Website URL', validators=[Required()],
        filters=[process_website_url])
    address = StringField('Venue')
    city = StringField('City', validators=[Length(1, 64)])
    state = StringField('State/Province')
    country = StringField('Country', validators=[Required()])
    start = DateField('Start date', validators=[Required()], format='%Y-%m-%d')
    end = DateField('End date', validators=[Required()], format='%Y-%m-%d')
    timezone = StringField('Time zone', validators=[Required()])
    info = TextAreaField('Conference information')
    subjects = SelectMultipleField(
        'Subjects', choices=[], validators=[Required()])
    tags = StringField('Tags')
    featured = BooleanField('Featured conference')
    contact_email = StringField('Contact email', validators=[Required(),
                                                             Length(1, 128),
                                                             Email()])
    contact_phone = StringField(
        'Contact phone number', validators=[Required()])
    your_role = StringField('Your role in the conference',
                            validators=[Required()])
    contact_name = StringField(
        'Name', validators=[Required()])
    affiliation = StringField(
        'Affiliation', validators=[Required()])
    requester_contact_phone = StringField(
        'Phone number', validators=[Required()])
    requester_website = StringField('Official website',
                                    filters=[process_website_url])
    referred_by = StringField('Referred by')
    source_from = SelectField(
        'How did you hear about us?',
        choices=[('Colleague', 'Colleague'),
                 ('Search Engine', 'Search Engine (Google, Bing...)'),
                 ('From a friend', 'From a friend'),
                 ('Link from another page', 'Link from another page'),
                 ('Business associate', 'Business associate')],
        validators=[Required()])
    submit_button = SubmitField('Submit')

    def __init__(self, **kwargs):
        super(ConferenceForm, self).__init__(**kwargs)
        with open(os.path.join(APP_STATIC, 'json/subjects.json')) as f:
            default_subjects = json.load(f)
            self.subjects.choices = [
                (value, value) for value in default_subjects]
            self.subjects.default = []

class ConferenceEditForm(Form):
    conference_name = StringField('Conference name', validators=[
        Required(), Length(1, 128)])
    short_name = StringField('Conference short name', validators=[
        Required(), Regexp('^[a-zA-Z_]{1,10}\d{4}$',
                           message="Incorrect Format"), Length(1, 64)])
    website_type = StringField('Website Type', validators=[Required(),
                                                           Length(1, 128)])
    website_url = StringField('Website URL', validators=[Required(),
                                                         Length(1, 128)])
    address = StringField('Venue')
    city = StringField('City', validators=[Length(1, 64)])
    state = StringField('State/Province', validators=[Length(0, 64)])
    country = StringField('Country', validators=[Required()])
    start = DateField('Start date', validators=[Required()], format='%Y-%m-%d')
    end = DateField('End date', validators=[Required()], format='%Y-%m-%d')
    timezone = StringField('Time zone', validators=[Required()])
    info = TextAreaField('Conference information')
    subjects = SelectMultipleField(
        'Subjects', choices=[], validators=[Required()])
    tags = StringField("Tags")
    featured = BooleanField('Featured conference')
    contact_email = StringField('Contact Email', validators=[Required(),
                                                             Length(1, 128),
                                                             Email()])
    contact_phone = StringField(
        'Contact Phone Number', validators=[Required()])
    submit = SubmitField('Update')

    def __init__(self, **kwargs):
        super(ConferenceEditForm, self).__init__(**kwargs)
        with open(os.path.join(APP_STATIC, 'json/subjects.json')) as f:
            default_subjects = json.load(f)
            self.subjects.choices = [(value, value) for value in default_subjects]
            self.subjects.default = []


class MultipleCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ConfigurationForm(Form):
    submission_choices = [('1', 'Open'), ('2', 'Close')]
    decision_types_choices = [
        ('1', 'Accept'), ('2', 'Possible Accept'), ('3', 'Reject'), ('4', 'Possible Reject')]
    conference_name = StringField('Conference Name', validators=[Required()])
    conference_acronym = StringField(
        'Conference Acronym', validators=[Required()])
    conference_website = StringField(
        'Conference Website', validators=[Required()])
    city = StringField('City', validators=[Required()])
    country = StringField('Contry', validators=[Required()])
    date = DateTimeField('Date', format='%m-%d-%Y', validators=[Required])
    open_close_submission = SelectField(
        'Open/Close Submission', choices=submission_choices)
    maximal_length_of_text_abstracts = IntegerField(
        'Maximal Length Of Text Abstracts', validators=[Required()])
    number_of_reviewer_per_paper = IntegerField(
        'Number of Reviewer Per Paper', validators=[Required()])
    decision_types = MultipleCheckboxField(
        'Decision Types', choices=decision_types_choices)
    submit = SubmitField('Submit')


class AutomaticAssignmentForm(Form):
    submit = SubmitField('Assign')
    # paper_status = SelectMultipleField('Paper status', choices=[])
    num_reviewers_paper = IntegerField(
        'Number of Reviewer Per Paper', validators=[Required()])
    algorithm = SelectField('Algorithm', choices=[('Random', 'Random')])

    def __init__(self, **kwargs):
        super(AutomaticAssignmentForm, self).__init__(**kwargs)
        reviewers = SelectMultipleField(
            'Reviewers', choices=[], validators=[Required()])
        self.reviewers = self._fields['reviewers'] = self.meta.bind_field(
            self, reviewers, {'name': 'reviewers', 'prefix': self._prefix})
        self.reviewers.process_data(None)


class NotificationForm(Form):
    email_content = TextAreaField(validators=[Required()])
    email_subject = StringField('Subject', validators=[
        Required(), Length(1, 128)])
    submit = SubmitField('Send')

    def validate_email_content(self, field):
        # check empty email content
        if field.data == '<p><br></p>':
            raise ValidationError('Empty email content')

    def __init__(self, type, **kwargs):
        super(NotificationForm, self).__init__(**kwargs)
        if type == 'author':
            status_select = SelectField(
                'Paper status',
                choices=[('Received', 'Received'),
                         ('Accepted', 'Accepted'),
                         ('Rejected', 'Rejected'),
                         ('Under Review', 'Under Review')])
            self.status_select = self._fields['status_select'] = \
                self.meta.bind_field(self, status_select,
                                     {'name': 'status_select',
                                      'prefix': self._prefix})
            self.status_select.process_data('Received')
            paper_ids = MultipleCheckboxField(
                'paper_ids', choices=[], coerce=int)
            self.paper_ids = self._fields['paper_ids'] = self.meta.bind_field(
                self, paper_ids,
                {'name': 'paper_ids', 'prefix': self._prefix})
            self.paper_ids.process_data(None)
        elif type == 'pc':
            email_receivers = SelectMultipleField(
                'Receivers', choices=[], validators=[Required()])
            self.email_receivers = self._fields['email_receivers'] = \
                self.meta.bind_field(self, email_receivers,
                                     {'name': 'email_receivers',
                                      'prefix': self._prefix})
            self.email_receivers.process_data(None)
            receiver_type = RadioField(
                '',
                choices=[('checkbox_all', 'checkbox_all'),
                         ('checkbox_missing','checkbox_missing'),
                         ('checkbox_complete','checkbox_complete'),
                         ('checkbox_other', 'checkbox_other')])
            self.receiver_type = self._fields['receiver_type'] = \
                self.meta.bind_field(self, receiver_type,
                                     {'name': 'receiver_type',
                                      'prefix': self._prefix})
            self.receiver_type.process_data('checkbox_all')
        elif type == 'member':
            email_receivers = SelectMultipleField(
                'Receivers', choices=[], validators=[Required()])
            self.email_receivers = self._fields['email_receivers'] = \
                self.meta.bind_field(self, email_receivers,
                                     {'name': 'email_receivers',
                                      'prefix': self._prefix})
        elif type == 'session':
            email_receivers = SelectMultipleField(
                'Receivers', choices=[], validators=[Required()])
            self.email_receivers = self._fields['email_receivers'] = \
                self.meta.bind_field(self, email_receivers,
                                     {'name': 'email_receivers',
                                      'prefix': self._prefix})
            receiver_type = RadioField(
                '',
                choices=[('checkbox_all', 'checkbox_all'),
                         ('checkbox_speakers', 'checkbox_speakers'),
                         ('checkbox_moderators', 'checkbox_moderators'),
                         ('checkbox_discussants', 'checkbox_discussants')])
            self.receiver_type = self._fields['receiver_type'] = \
                self.meta.bind_field(self, receiver_type,
                                     {'name': 'receiver_type',
                                      'prefix': self._prefix})
            self.receiver_type.process_data('checkbox_all')


class TrackNotificationForm(Form):
    email_subject = StringField('Subject', validators=[
        Required(), Length(1, 128)])
    email_receivers = SelectMultipleField(
        'Receivers', choices=[], coerce=int, validators=[Required()])
    track_list = SelectField('Track list', choices=[],
                             coerce=int, validators=[Required()])
    email_content = TextAreaField(validators=[Required()])
    submit = SubmitField('Send')


class RegistrationForm(Form):
    card_number = StringField('Credit card number', validators=[Required()])
    holder_name = StringField('Name on card', validators=[
        Required(), Length(1, 128)])
    security_code = IntegerField('Security code', validators=[Required()])
    # expire_date = StringField('Expire date', validators=[
    #                           Required(), Length(1, 7)])
    month = SelectField('Month:', choices=[('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), ('4', 'Apr'), ('5', 'May'),
                                           ('6', 'June'), ('7', 'July'), ('8', 'Aug'), ('9', 'Sept'), ('10', 'Oct'),
                                           ('11', 'Nov'), ('12', 'Dec')], validators=[Required()])
    year = SelectField('Year:', validators=[Required()])
    street = StringField('Street', validators=[Required(), Length(1, 128)])
    city = StringField('City', validators=[Required(), Length(1, 128)])
    state = StringField(
        'State/Province', validators=[Length(0, 128)])
    zipcode = IntegerField('Zip', validators=[Optional()])
    country = StringField('Country', validators=[Required()])
    # email = StringField('Buyer\'s mail', validators=[Required(), Email()])
    submit_button = SubmitField('Confirm')
    attendee_first_name = StringField('Attendee\'s first name', validators=[
        DataRequired(), Length(1, 128), name_validator])
    attendee_last_name = StringField('Attendee\'s last name', validators=[
        Required(), Length(1, 128), name_validator])
    attendee_email = StringField(
        'Attendee\'s email', validators=[Required(),  Length(1, 128), Email()])
    attendee_affiliation = StringField('Attendee\'s Affiliation', validators=[
        Required(), Length(1, 128)])
    tickets = RadioField(coerce=int, validators=[Required()])
    products = SelectMultipleField(coerce=int)
    promo_code = HiddenField()
    stripeToken = HiddenField()

    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)

        now = time.localtime()[0]
        expire_year = []
        for year in range(now, now + 10):
            expire_year.append((str(year), str(year)))
        self.year.choices = expire_year


class SetRegistrationForm(Form):
    # start = DateField('Start date', validators=[Required()], format='%Y-%m-%d')
    # end = DateField('End date', validators=[Required()], format='%Y-%m-%d')
    num_of_tickets = IntegerField(default=1)
    submit = SubmitField('Confirm')


class PayoutForm(Form):
    account_name = StringField('Personal or Company name on account *',
                               validators=[Required(), Length(1, 128)])
    address_1 = StringField('Address line 1 *',
                            validators=[Required(), Length(1, 128)])
    address_2 = StringField('Address line 2',
                            validators=[Length(0, 128)])
    city = StringField('City *',
                       validators=[Required(), Length(1, 64)])
    state = StringField('State',
                        validators=[Length(0, 64)])
    country = StringField('Country *',
                          validators=[Required(), Length(1, 128)])
    zipcode = StringField('Zipcode',
                          validators=[Length(0, 8)])
    payment_method = SelectField('Payment methods',
                                 validators=[Required()],
                                 choices=[('Direct Deposit', 'Direct Deposit'),
                                          ('Check', 'Check')])
    bank_name = StringField('Bank name *',
                            validators=[Length(0, 128)])
    account_type = SelectField('Account type',
                               choices=[('Checking', 'Checking'),
                                        ('Savings', 'Savings')])
    routing_number = StringField('Routing number *',
                                 validators=[Length(0, 9)])
    account_number = StringField('Account number *',
                                 validators=[Length(0, 32)])
    submit = SubmitField('Save')


class InvitationsForm(Form):
    emails_default = TextAreaField(
        'Invite people with selected role')
    role = SelectField('Role', choices=[('User', 'User'),
                                        ('Program Committee',
                                         'Program Committee'),
                                        ('Chair', 'Chair')],
                       validators=[Required()])
    track_id = SelectField('Track')
    email_subject = StringField('Subject', validators=[
        Required(), Length(1, 128)])
    email_content = TextAreaField(validators=[Required()])
    invitee_with_name = BooleanField('Include invitee\'s name on invitation')
    submit = SubmitField('Invite New Members')

    def validate_invitees_emails(self, conference):
        emails_default = split_on_comma_and_trim(self.emails_default.data)
        # Since emails.errors is a tuple we want to convert it to a list for
        # now.
        emails_default_errors_list = list(self.emails_default.errors)
        valid_emails_default = []
        # Check if any bad emails or emails already in the database.
        if not emails_default:
            emails_default_errors_list.append(
                'Please input at least one email address')
        for email in emails_default:
            if not re.match(
                    r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$", email):
                emails_default_errors_list.append(
                    email + ' is not a valid email address.')
            else:
                # selected role in the invitation
                # check if the user already existed
                user = User.query.filter_by(email=email).first()
                if self.track_id is None:
                    track_id = conference.tracks.filter_by(
                        default=True).first().id
                    joined_msg = ' already joined the conference, please \
                    update the role in <a href="' + \
                        url_for('conference.conferences_members',
                                conference_id=conference.id) + \
                        '">conference members</a> panel.'
                else:
                    track_id = self.track_id.data
                    joined_msg = ' already joined the conference, please update the role in <a href="' + \
                                 url_for('conference.track_members', conference_id=conference.id) + \
                                 '">track members</a> panel.'
                prev_invitaion = conference.invitations.filter_by(invitee_email=email,
                                                                  invitee_status='Pending', track_id=track_id).first()
                if user:
                    if user.is_joined_track(conference.tracks.filter_by(id=track_id).first()):
                        emails_default_errors_list.append(
                            email + joined_msg)

                    else:
                        valid_emails_default.append(email)
                # check whether same invitations of this conference
                elif prev_invitaion:
                    if prev_invitaion.invitee_role == self.role.data:
                        emails_default_errors_list.append(
                            email + ' has already been invited as ' + self.role.data + '. You can resend the invitation.')
                    else:
                        # revoked by db listener
                        emails_default_errors_list.append(
                            email + '\'s previous invitation is revoked. New invitation has been sent.')
                        valid_emails_default.append(email)
                else:
                    valid_emails_default.append(email)
        # eliminate duplicate emails
        valid_emails_default = list(set(valid_emails_default))
        self.emails_default.errors = tuple(emails_default_errors_list)
        # clear the emails textarea
        self.emails_default.data = ''
        return valid_emails_default

    def validate_invitees_names_emails(self, conference):
        emails_default = split_on_return(self.emails_default.data)
        # Since emails.errors is a tuple we want to convert it to a list for
        # now.
        emails_default_errors_list = list(self.emails_default.errors)

        valid_emails_default = []
        # Check if any bad emails or emails already in the database.
        if not emails_default:
            emails_default_errors_list.append(
                'Please input at least one email address')
        for invitee_info in emails_default:
            if not invitee_info:
                continue
            # last_name = invitee_info[1]
            # first_name = invitee_info[0]
            if len(invitee_info) != 3 or not re.match(
                    r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$",
                    invitee_info[2]):
                emails_default_errors_list.append(
                    ' '.join(invitee_info) + ' is invalid.')
            else:
                # selected role in the invitation
                # role = Role.query.filter_by(name=self.role.data).first()
                # check if the user already existed
                email = invitee_info[2]
                user = User.query.filter_by(email=email).first()
                if self.track_id is None:
                    track_id = conference.tracks.filter_by(
                        default=True).first().id
                else:
                    track_id = self.track_id.data
                prev_invitaion = conference.invitations.filter_by(
                    invitee_email=email,
                    invitee_status='Pending', track_id=track_id).first()
                if user:
                    if user.is_joined_conference(conference):
                        emails_default_errors_list.append(
                            email + ' already joined the conference, please \
                            update the role in members page.')
                    else:
                        valid_emails_default.append(invitee_info)
                # check whether same invitations of this conference
                elif prev_invitaion:
                    if prev_invitaion.invitee_role == self.role.data:
                        emails_default_errors_list.append(' '.join(
                            invitee_info) + ' has already been invited as ' +
                            self.role.data +
                            '. You can resend the invitation.')
                    else:
                        # revoked by db listener
                        emails_default_errors_list.append(' '.join(
                            invitee_info) + '\'s previous invitation is \
                            revoked. New invitation has been sent.')
                        valid_emails_default.append(invitee_info)
                else:
                    valid_emails_default.append(invitee_info)
        # eliminate duplicate emails
        valid_emails_default = list(set(valid_emails_default))
        self.emails_default.errors = tuple(emails_default_errors_list)
        # clear the emails textarea
        self.emails_default.data = ''

        return valid_emails_default
