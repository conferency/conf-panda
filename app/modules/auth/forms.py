from flask_wtf import Form
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo
from wtforms import ValidationError
from ...models import User


class LoginForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 128),
                                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    # for preview control
    # code = StringField('Code', validators=[DataRequired(), Length(1, 64)])
    # remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

    # def validate_code(self, field):
    #     if field.data != "confpanda2016":
    #         raise ValidationError('Invalid Preview Code')


class RegistrationForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 128),
                        Email()])
    firstname = StringField('First Name', validators=[
                            DataRequired(), Length(1, 64)])
    lastname = StringField('Last Name', validators=[
                           DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    organization = StringField('Organization', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])
    location = StringField('City', validators=[DataRequired()])
    state = StringField('State/Province', validators=[Length(0, 64)])
    # for preview control
    # code = StringField('Code', validators=[DataRequired(), Length(1, 64)])
    submit = SubmitField('Register')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError(
                'Password must be at least 8 characters long')
    # def validate_code(self, field):
    #     if field.data != "confpanda2016":
    #         raise ValidationError('Invalid Preview Code')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class InvitationRegistrationForm(Form):
    firstname = StringField('First Name', validators=[
                            DataRequired(), Length(1, 64)])
    lastname = StringField('Last Name', validators=[
                           DataRequired(), Length(1, 64)])
    password = PasswordField('Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    organization = StringField('Organization', validators=[DataRequired()])
    country = StringField('Country', validators=[DataRequired()])
    location = StringField('City', validators=[DataRequired()])
    state = StringField('State/Province', validators=[Length(0, 64)])
    note = TextAreaField('Leave a message to the inviter')
    submit = SubmitField('Register')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError(
                'Password must be at least 8 characters long')


class InvitationDeclineForm(Form):
    note = TextAreaField('Leave a message to the inviter')
    submit = SubmitField('Submit')


class ReviewRequestDeclineForm(Form):
    email = StringField('Email address which received the review request',
                        validators=[DataRequired(), Length(1, 128), Email()])
    note = TextAreaField('Leave a message to the PC',
                         validators=[DataRequired()])
    submit = SubmitField('Submit')


class ChangePasswordForm(Form):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[
        EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm new password',
                              validators=[DataRequired()])
    submit = SubmitField('Update Password')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError(
                'Password must be at least 8 characters long')


class PasswordResetRequestForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 128),
                                             Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(Form):
    password = PasswordField('New Password', validators=[
        DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[DataRequired()])
    submit = SubmitField('Reset Password')

    def validate_password(self, field):
        if len(field.data) < 8:
            raise ValidationError(
                'Password must be at least 8 characters long')


class ChangeEmailForm(Form):
    email = StringField('New Email', validators=[DataRequired(),
                                                 Length(1, 128),
                                                 Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


class MergeForm(Form):
    email = StringField('Email', validators=[DataRequired(),
                                             Length(1, 256),
                                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Merge this account into your current account')

    def validate_email(self, field):
        if not User.query.filter_by(email=field.data).first():
            raise ValidationError('Account doesn\'t exist.')


class ChangeSettingForm(Form):
    hide_tour = BooleanField('Hide Tour?', default=False)
    submit = SubmitField('Update Personal Settings')


class TimeoutForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 128),
                                             Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    token = StringField('Token',  validators=[DataRequired()])

    submit = SubmitField('Log In')

    def __init__(self, *args, **kwargs):
        super(TimeoutForm, self).__init__(*args, **kwargs)
        self.TIME_LIMIT = 0
