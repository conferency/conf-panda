# -*- coding: utf-8 -*-
import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'FUxT2szXsj5KvKgQ'

    # SQL Alchemy Configurations
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_RECORD_QUERIES = True
    # disable significant overhead from sqlachemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Email Configurations
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    CONF_MAIL_SUBJECT_PREFIX = '[Conferency]'
    CONF_MAIL_SENDER = os.environ.get('CONF_MAIL_SENDER') or \
        'Conferency <no-reply@conferency.com>'
    CONF_ADMIN = os.environ.get('CONF_ADMIN') or 'admin@conferency.com'
    CONF_SUPPORT = os.environ.get('CONF_SUPPORT') or 'support@conferency.com'

    # Flask Upload Size - Not in Flask-Uploads, this is set to 15M
    # There is Nginx upload limit set in the server config file: 100M
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024

    # Flask-Uploads configs - used in /app/__init__.py
    # the names has the format: UPLOADED_[]_DEST defined by Flask-Uploads
    UPLOADED_PAPERS_DEST = os.environ.get(
        'UPLOADED_PAPERS_DEST') or basedir + '/app/static/upload/papers/'
    UPLOADED_TEMPPAPERS_DEST = os.environ.get(
        'UPLOADED_TEMPPAPERS_DEST') or basedir + '/app/static/upload/temp/'
    UPLOADED_AVATAR_DEST = os.environ.get(
        'UPLOADED_AVATAR_DEST') or basedir + '/app/static/upload/avatar/'

    # PDF static server configurations
    PDF_URL = os.environ.get('PDF_URL') or "static/upload/papers/"
    TEMP_URL = os.environ.get('TEMP_URL') or "static/upload/temp/"
    ZIP_URL = basedir + "/app/static/conference_tarballs/"

    # CONF Configurations
    CONF_POSTS_PER_PAGE = 20
    CONF_FOLLOWERS_PER_PAGE = 20
    CONF_COMMENTS_PER_PAGE = 30
    CONF_SLOW_DB_QUERY_TIME = 0.5

    # Celery Configurations
    # AWS Setting, the server and redis must be in the same VPC

    # CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    # CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
    CELERY_BROKER_URL = 'amqp://conf_mail:conf2018@18.179.41.78:5672/conf_mail_mq'
    CELERY_RESULT_BACKEND = 'amqp://conf_mail:conf2018@18.179.41.78:5672/conf_mail_mq'
    # stripe keys
    STRIPE_SECRET_KEY = os.environ.get(
        'STRIPE_SECRET_KEY') or 'sk_test_deao2OeQJ2X6UkCNxJD34GNN'
    STRIPE_PUBLISHABLE_KEY = os.environ.get(
        'STRIPE_PUBLISHABLE_KEY') or 'pk_test_hSe5iIjoO6wwuSmt6JDJ13hX'

    CONF_WORDPRESS_DOMAIN = os.environ.get('CONF_WORDPRESS_DOMAIN') or \
        'http://sites.conferency.com'

    # for s3 backup
    AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
    AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')
    PAPER_BUCKET = os.environ.get('PAPER_BUCKET')
    S3_ENDPOINT = os.environ.get('S3_ENDPOINT')

    # session
    import datetime
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=30)

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    # debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    DEBUG_TB_PROFILER_ENABLED = True
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite')


    # Faster session expiry
    import datetime
    PERMANENT_SESSION_LIFETIME = datetime.timedelta(minutes=15)


class TestingConfig(Config):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'data-test.sqlite')
    CONF_MAIL_SENDER = 'Conferency <no-reply@conferency.com>'


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+mysqldb://root@localhost/conferency?charset=utf8'

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        from logging import Formatter
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.CONF_MAIL_SENDER,
            toaddrs=[cls.CONF_ADMIN],
            subject=cls.CONF_MAIL_SUBJECT_PREFIX +
            ' Production Application Error!',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        mail_handler.setFormatter(Formatter('''
        Message type:       %(levelname)s
        Location:           %(pathname)s:%(lineno)d
        Module:             %(module)s
        Function:           %(funcName)s
        Time:               %(asctime)s

        Message:

        %(message)s
        '''))
        app.logger.addHandler(mail_handler)


class DemoConfig(ProductionConfig):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(
        basedir, 'data-dev.sqlite')


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    'demo': DemoConfig
}
