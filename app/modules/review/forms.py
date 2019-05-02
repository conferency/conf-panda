from flask.ext.wtf import Form
from wtforms import SelectField, TextAreaField, RadioField, SubmitField, StringField, TextAreaField
from wtforms.validators import Required, DataRequired, Length, Email

from app.utils.regex import name_validator


class ReviewForm(Form):
    # paper_select = SelectField(
    #     "Paper", choices=[], coerce=int, validators=[Required()])
    evaluation = RadioField("Overall Evaluation *",
                            choices=[(1, 'Reject'), (2, 'Weak Reject'), (3, 'Borderline'),
                                     (4, 'Weak Accept'), (5, 'Accept')],
                            coerce=int, validators=[Required()])
    confidence = RadioField("Reviewer Confidence *",
                            choices=[(1, 'None'), (2, 'Low'),
                                     (3, 'Medium'), (4, 'High'), (5, 'Expert')],
                            coerce=int, validators=[Required()])
    review_body = TextAreaField("Review *", validators=[Required()])
    confidential_remarks = TextAreaField("Confidential Remarks")
    submit = SubmitField('Submit')


class ReviewRequestForm(Form):
    email = StringField('Email', validators=[DataRequired(), Length(1, 128),
                                             Email()])
    firstname = StringField('First Name', validators=[
                            DataRequired(), Length(1, 64), name_validator])
    lastname = StringField('Last Name', validators=[
                           DataRequired(), Length(1, 64), name_validator])
    subject = StringField('Subject', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    submit = SubmitField('Send')
