# -*- coding: utf-8 -*-
"""Init for conferency."""

from flask import Flask, request_finished, g, url_for
# from flask.ext.bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
# from flask.ext.pagedown import PageDown
from flask_uploads import configure_uploads, UploadSet
# from flask_debugtoolbar import DebugToolbarExtension
# from flask.ext.admin import Admin
from celery import Celery
from config import config
import os
import time
# from utils.macros import format_date_thedaybefore, check_date, format_date,\
#    timestamp, product_has_sold, generate_timeout_token
# from utils.template import generate_navigation_bar
# import flask_excel as excel
# import stripe
import warnings


# toolbar = DebugToolbarExtension()
# bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()
# pagedown = PageDown()
# db_admin = Admin(name='Conferency', template_mode='bootstrap3',
#                  endpoint='administration', url='/admin/dbop')
celery = Celery()

# Flask-Uploads
PDF = ('pdf',)
WORD = ('doc', 'docx')
uploaded_papers = UploadSet('papers', PDF)
uploaded_papers_with_docx = UploadSet('papers', PDF + WORD)
uploaded_papers_without_pdf = UploadSet('papers', WORD)
uploaded_temppapers = UploadSet('temppapers', PDF)

login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'

# for reading files
APP_ROOT = os.path.dirname(os.path.abspath(
    __file__))  # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'static')


def create_app(config_name):
    app = Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # excel.init_excel(app)
    # bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    # pagedown.init_app(app)
    configure_uploads(app, (uploaded_papers, uploaded_papers_with_docx,
                            uploaded_temppapers))

    # celery.conf.update(app.config)
    # class ContextTask(celery.Task):
    #    def __call__(self, *args, **kwargs):
    #        with app.app_context():
    #            return self.run(*args, **kwargs)
    # celery.Task = ContextTask

    # toolbar.init_app(app)
    # db_admin.init_app(app)

    # convert unicode to string
    # app.jinja_env.filters['split'] = str.split
    # app.jinja_env.filters['str'] = str
    # app.jinja_env.filters['date_thedaybefore'] = format_date_thedaybefore
    # app.jinja_env.filters['date'] = format_date
    # app.jinja_env.filters['unix_time'] = time.mktime
    # app.jinja_env.filters['product_has_sold'] = product_has_sold

    # add test equalto which is included in 2.8
    # app.jinja_env.tests['equalto'] = lambda value, other: value == other
    # import function
    # app.jinja_env.globals.update(
    #     check_date=check_date,
    #     generate_navigation_bar=generate_navigation_bar,
    #     timestamp=timestamp)

    # flask admin
    # admin = Admin(app, name='', template_mode='bootstrap3')
    # from .modules.admin.views import UserView, PaperView, AuthorView, \
    #     ConferenceView
    # with warnings.catch_warnings():
    #     warnings.filterwarnings(
    #         'ignore', 'Fields missing from ruleset', UserWarning)
    #     admin.add_view(UserView(db.session, name='Users',
    #                             endpoint='admin_user'))
    #     admin.add_view(PaperView(db.session, name='Papers',
    #                              endpoint='admin_paper'))
    #     admin.add_view(AuthorView(db.session, name='Author',
    #                               endpoint='admin_author'))
    #     admin.add_view(ConferenceView(db.session, name='Conference',
    #                                   endpoint='admin_conference'))
    # inject stripe key
    # with app.app_context():
    #     stripe.api_key = app.config['STRIPE_SECRET_KEY']

    @app.context_processor
    def processor():
        return {
            'PERMANENT_SESSION_LIFETIME_MS':
            (app.permanent_session_lifetime.seconds * 1000),
            'generate_timeout_token': generate_timeout_token,
            'debug': app.debug,
        }

    if config_name == 'production':
        pass
    else:
        @app.context_processor
        def override_url_for():
            return dict(url_for=dated_url_for)

        def dated_url_for(endpoint, **values):
            if endpoint == 'static':
                filename = values.get('filename', None)
                if filename:
                    file_path = os.path.join(app.root_path,
                                             endpoint, filename)
                    values['q'] = int(os.stat(file_path).st_mtime)
            return url_for(endpoint, **values)

    @app.before_request
    def record_request():
        g.request_start_time = time.time()

    # log all the request and response
    from .utils.request_log import add_request
    request_finished.connect(add_request, app)

    # Add current_app.permanent_session_lifetime converted to milliseconds
    # to context. The config variable PERMANENT_SESSION_LIFETIME is not
    # used because it could be either a timedelta object or an integer
    # representing seconds.
    # current_endpoint is string representing current endpoint

    #from .modules.main import main as main_blueprint
    #app.register_blueprint(main_blueprint)

    #from .modules.tasks import tasks as tasks_blueprint
    #app.register_blueprint(tasks_blueprint)

    #from .modules.auth import auth as auth_blueprint
    #app.register_blueprint(auth_blueprint, url_prefix='/auth')

    #from .modules.conf_admin import conf_admin as conf_admin_blueprint
    #app.register_blueprint(conf_admin_blueprint, url_prefix='/conf_admin')

    # from modules.db_admin import db_admin as db_admin_module
    # db_admin.add_view(db_admin_module)

    #from .modules.submission import submission as submission_blueprint
    #app.register_blueprint(submission_blueprint, url_prefix='/submission')

    #from .modules.review import review as review_blueprint
    #app.register_blueprint(review_blueprint, url_prefix='/review')

    #from .modules.paper import paper as paper_blueprint
    #app.register_blueprint(paper_blueprint, url_prefix='/paper')

    #from .modules.conference import conference as conference_blueprint
    #app.register_blueprint(conference_blueprint, url_prefix='/conference')

    #from .modules.website import website as website_blueprint
    #app.register_blueprint(website_blueprint, url_prefix='/website')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    return app
