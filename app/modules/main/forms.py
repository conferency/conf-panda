import time

# from flask.ext.pagedown.fields import PageDownField
from flask_wtf import Form
from wtforms import StringField, TextAreaField, BooleanField, SelectField, \
    SubmitField, RadioField, HiddenField, SelectMultipleField, IntegerField
from wtforms import ValidationError
from wtforms.validators import Required, Length, Email, Optional

from ...models import User


class NameForm(Form):
    name = StringField('What is your name?', validators=[Required()])
    submit = SubmitField('Submit')


class EditProfileForm(Form):
    first_name = StringField(
        'First Name *', validators=[Required(), Length(1, 64)])
    last_name = StringField(
        'Last Name *', validators=[Required(), Length(1, 64)])
    organization = StringField(
        'Organization *', validators=[Required(), Length(1, 256)])
    country = StringField('Country *', validators=[Required()])
    state = StringField('State/Province', validators=[Length(0, 64)])
    location = StringField('City *', validators=[Required(), Length(1, 64)])
    website = StringField('Website')
    about_me = TextAreaField('About Me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(Form):
    email = StringField('Email', validators=[Required(), Length(1, 128),
                                             Email()])
    confirmed = BooleanField('Confirmed')
    # a bug here
    # role = SelectField('Role', coerce=int)
    first_name = StringField('First Name', validators=[
                             Required(), Length(0, 64)])
    last_name = StringField('Last Name', validators=[
                            Required(), Length(0, 64)])
    location = StringField('City', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        # self.role.choices = [(role.id, role.name)
        # for role in Role.query.order_by(Role.name).all()]
        self.user = user

    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')


# class PostForm(Form):
#     body = PageDownField("What's on your mind?", validators=[Required()])
#     submit = SubmitField('Submit')


class CommentForm(Form):
    body = StringField('Enter your comment', validators=[Required()])
    submit = SubmitField('Submit')


class TicketOrderForm(Form):
    collection_type = RadioField('Collection type', choices=[('basic_info', 'Basic information'),
                                                             ('buy_only', 'Buyer only'), ('each_attendee', 'Each Attendee')], validators=[Required()])
    ticket_type = SelectMultipleField('Select information by ticket type', choices=[('early_acad', 'Early academic'),
                                                                                    ('early_stud', 'Early student')], validators=[Required()])
    email = StringField('Email', validators=[
                        Required(), Length(1, 128), Email()])


class RegistrationForm(Form):
    card_number = StringField('Credit card number', validators=[Required()])
    holder_name = StringField('Name on card', validators=[
                              Required(), Length(1, 128)])
    security_code = IntegerField('Security code', validators=[Required()])
    # expire_date = StringField('Expire date', validators=[
    #                           Required(), Length(1, 7)])
    month = SelectField('Month:', choices=[('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), ('4', 'Apr'), ('5', 'May'),
                                           ('6', 'June'), ('7', 'July'), ('8', 'Aug'), ('9', 'Sept'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec')], validators=[Required()])
    year = SelectField('Year:', validators=[Required()])
    street = StringField('Street', validators=[Required(), Length(1, 128)])
    city = StringField('City', validators=[Required(), Length(1, 128)])
    state = StringField(
        'State/Province', validators=[Length(0, 128)])
    zipcode = IntegerField('Zip', validators=[Optional()])
    country = StringField('Country', validators=[Required()])
    # email = StringField('Buyer\'s mail', validators=[Required(), Email()])
    submit_button = SubmitField('Confirm')
    attendee_first_name = StringField('First name', validators=[
        Required(), Length(1, 128)])
    attendee_last_name = StringField('Last name', validators=[
        Required(), Length(1, 128)])
    attendee_email = StringField(
        'Email', validators=[Required(), Email()])
    attendee_affiliation = StringField('Affiliation', validators=[
        Required(), Length(1, 128)])
    tickets = RadioField(coerce=int, validators=[Required()])
    products = SelectMultipleField(coerce=int)
    promo_code = HiddenField()
    stripeToken = HiddenField()

    def __init__(self,*args, **kwargs):
        super(RegistrationForm,self).__init__(*args, **kwargs)
        current_year = time.localtime().tm_year
        expire_year = []
        for year in range(current_year, current_year+10):
            expire_year.append((str(year), str(year)))
        self.year.choices = expire_year
