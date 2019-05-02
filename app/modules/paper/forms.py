from flask.ext.wtf import Form
from wtforms import SubmitField, TextAreaField, StringField, HiddenField, \
    SelectField
from wtforms.validators import Required


class WithdrawForm(Form):
    # subject = StringField("Subject", validators=[Required()])
    message = TextAreaField("Message", validators=[Required()])
    submit = SubmitField('Withdraw')


class PaperForm(Form):
    filename = HiddenField()
    title = StringField('Title *', validators=[Required()])
    abstract = TextAreaField('Abstract *', validators=[Required()])
    keywords = StringField('Keywords  *', validators=[Required()])
    track_id = SelectField('Tracks *', coerce=int)
    comment = TextAreaField('Comment')
