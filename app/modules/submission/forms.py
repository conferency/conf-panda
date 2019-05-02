from flask.ext.wtf import Form
from wtforms import StringField, TextAreaField, HiddenField, SelectField
from wtforms.validators import Required


class PaperForm(Form):
    filename = HiddenField()
    title = StringField('Title *', validators=[Required()])
    abstract = TextAreaField('Abstract *', validators=[Required()])
    keywords = StringField('Keywords  *', validators=[Required()])
    track_id = SelectField('Tracks *', coerce=int)
    comment = TextAreaField('Comment')
