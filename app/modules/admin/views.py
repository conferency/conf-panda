from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.login import current_user
from wtforms import StringField
from wtforms.validators import Required, Length, Email
from ...models import User, Paper, Author, Conference

class UserView(ModelView):

    column_labels = {
        'id': 'ID',
        'first_name': 'First name',
        'last_name': 'Last name',
        'email': 'Email'
    }

    column_list = ('id', 'first_name', 'last_name', 'email')
    form_create_rules = ('first_name', 'last_name', 'email', 'organization',
                         'location', 'state', 'country', 'website', 'about_me')
    form_edit_rules = ('first_name', 'last_name', 'email', 'organization',
                       'location', 'state', 'country', 'website', 'about_me')
    column_searchable_list = ['first_name', 'last_name', 'email', 'id']
    column_filters = ['first_name', 'last_name', 'organization',
                      'location', 'state', 'country']

    def __init__(self, session, **kwargs):
        super(UserView, self).__init__(User, session, **kwargs)

    def is_accessible(self):
        if current_user.is_administrator():
            return True
        return False

    def scaffold_form(self):
        form_class = super(UserView, self).scaffold_form()
        form_class.email = StringField('Email', validators=[Length(1, 128), Email()])
        return form_class


class PaperView(ModelView):

    column_labels = {
        'id': 'ID',
        'title': 'Title',
        'uploader_id': 'Uploader ID',
        'keywords': 'Keywords'
    }

    column_list = ('id', 'title', 'uploader_id', 'keywords')
    form_create_rules = ('title', 'abstract', 'keywords')
    form_edit_rules = ('title', 'abstract', 'keywords')

    column_searchable_list = ['title', 'keywords', 'abstract', 'id',
                              'uploader.first_name', 'uploader.last_name',
                              'authors.first_name', 'authors.last_name']
    column_filters = ['title', 'keywords', 'abstract', 'id',
                      'uploader.first_name', 'uploader.last_name',
                      'authors.first_name', 'authors.last_name']

    def __init__(self, session, **kwargs):
        super(PaperView, self).__init__(Paper, session, **kwargs)

    def is_accessible(self):
        if current_user.is_administrator():
            return True
        return False


class AuthorView(ModelView):

    column_labels = {
        'id': 'ID',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email'
    }

    form_columns = ['first_name', 'last_name', 'email',
                    'organization', 'country', 'website', 'paper_id']
    column_list = ('id', 'first_name', 'last_name', 'email', 'paper_id')
    form_create_rules = ('first_name', 'last_name', 'email',
                         'organization', 'country', 'website', 'paper_id')
    form_edit_rules = ('first_name', 'last_name', 'email',
                       'organization', 'country', 'website', 'paper_id')

    column_searchable_list = ['first_name', 'last_name', 'email',
                              'organization', 'country', 'website',
                              'paper.title', 'paper.abstract',
                              'paper.keywords']
    column_filters = ['first_name', 'last_name',
                      'organization', 'country', 'website',
                      'paper.title', 'paper.abstract', 'paper.keywords']

    def __init__(self, session, **kwargs):
        super(AuthorView, self).__init__(Author, session, **kwargs)

    def is_accessible(self):
        if current_user.is_administrator():
            return True
        return False

    def scaffold_form(self):
        form_class = super(AuthorView, self).scaffold_form()
        form_class.email = StringField('Email', validators=[Length(1, 128), Email()])
        return form_class

class ConferenceView(ModelView):
    column_labels = {
        'name': 'Conference name',
        'short_name': 'Conference short name',
        'website': 'Website',
        'contact_email': 'Contact Email',
        'contact_phone': 'Contact Phone Number',
        'city': 'City',
        'state': 'State/Province',
        'country': 'Country',
        'address': 'Venue',
        'start_date': 'Start date',
        'end_date': 'end date',
        'timezone': 'Time zone',
        'subjects': 'Subjects',
        'tags': 'Tags',
        'info': 'Conference information'
    }

    column_list = ('name', 'short_name', 'website', 'contact_email', 'contact_phone', 'city', 'state', 'country',
                   'address', 'start_date', 'end_date', 'timezone', 'subjects', 'tags', 'info')
    form_create_rules = ('name', 'website', 'contact_email', 'contact_phone', 'city', 'state', 'country',
                   'address', 'start_date', 'end_date', 'timezone', 'subjects', 'tags', 'info')
    form_edit_rules = ('name', 'short_name', 'website', 'contact_email', 'contact_phone', 'city', 'state', 'country',
                   'address', 'start_date', 'end_date', 'timezone', 'subjects', 'tags', 'info')
    column_searchable_list = ['name', 'short_name', 'website', 'contact_phone', 'city', 'state', 'country',
                   'address', 'start_date', 'end_date', 'timezone', 'subjects', 'tags', 'info']
    column_filters = ['name', 'short_name', 'website', 'contact_phone', 'city', 'state', 'country',
                   'address', 'start_date', 'end_date', 'timezone', 'subjects', 'tags', 'info']

    def __init__(self, session, **kwargs):
        super(ConferenceView, self).__init__(Conference, session, **kwargs)

    def is_accessible(self):
        if current_user.is_administrator():
            return True
        return False

    def scaffold_form(self):
        form_class = super(ConferenceView, self).scaffold_form()
        form_class.contact_email = StringField('Email', validators=[Length(1, 128), Email()])
        return form_class
