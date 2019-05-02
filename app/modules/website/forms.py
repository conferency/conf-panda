from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, HiddenField, SelectField, IntegerField, SubmitField
from wtforms.validators import Required, Length


class SiteActivationForm(Form):
    title = StringField("Site Title *", validators=[Required()])
    submit = SubmitField('Submit')
