#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import glob
from app import create_app, db
from app.utils.fakedata import generate_test_confs, generate_fake_tickets, \
    generate_test_users, generate_fake_papers, generate_fake_reviews, \
    generate_fake_transactions, generate_fake_schedule, \
    generate_default_addons, generate_admin, generate_fake_confs, \
    generate_main_conf
from app.models import User, Follow, Role, Permission, Post, Comment, Paper, \
    Review, PaperStatus, Invitation, Configuration, Conference, Ticket, \
    EmailTemplate, JoinTrack, Author, TicketTransaction, Track, \
    Registration, FormConfiguration, PromoCode, Product, ProductOption, \
    Payout, Website, Page, UserDoc, Todo, EventLog, DelegateReview, \
    ConferenceSchedule, Session, ReviewPreference, RequestLog, \
    ConferencePayment, ConferenceTransaction, ConferenceAddon, ReviewComment, \
    FavSession, TicketPrice, paper_reviewer, paper_author
from flask_script import Manager, Shell, Server
from flask_migrate import Migrate, MigrateCommand
from config import config

COV = None
if os.environ.get('FLASK_COVERAGE'):
    import coverage
    COV = coverage.coverage(branch=True, include='app/*')
    COV.start()
    print('Test Coverage Analysis Starting')

if os.path.exists('.env'):
    print('Importing environment from .env...')
    for line in open('.env'):
        var = line.strip().split('=')
        if len(var) == 2:
            os.environ[var[0]] = var[1]


# get config
app = create_app(os.getenv('CONF_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


@migrate.configure
def configure_alembic(c):
    # modify config object
    c.set_main_option('compare_type', 'True')
    return c


def make_shell_context():
    return dict(app=app, db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Todo=Todo, Comment=Comment,
                Paper=Paper, Review=Review, PaperStatus=PaperStatus,
                Invitation=Invitation, Configuration=Configuration,
                Conference=Conference, Track=Track,
                EmailTemplate=EmailTemplate, JoinTrack=JoinTrack,
                Author=Author, ConferenceSchedule=ConferenceSchedule,
                TicketTransaction=TicketTransaction, Ticket=Ticket,
                Registration=Registration, FormConfiguration=FormConfiguration,
                PromoCode=PromoCode, Product=Product, Session=Session,
                ProductOption=ProductOption, Payout=Payout, Website=Website,
                Page=Page, UserDoc=UserDoc, EventLog=EventLog,
                DelegateReview=DelegateReview,
                ReviewPreference=ReviewPreference, RequestLog=RequestLog,
                ConferencePayment=ConferencePayment,
                ConferenceTransaction=ConferenceTransaction,
                ConferenceAddon=ConferenceAddon, ReviewComment=ReviewComment,
                FavSession=FavSession, TicketPrice=TicketPrice,
                paper_reviewer=paper_reviewer, paper_author=paper_author)


manager.add_command('shell', Shell(make_context=make_shell_context))
manager.add_command('db', MigrateCommand)
manager.add_command('runserver', Server(threaded=True))


@manager.command
def test_logging():
    """Test logging."""
    app.logger.error('This is a error log test')
    app.logger.info('This is a info log test')


@manager.command
def test(coverage=False):
    """Run the unit tests."""
    # enable test coverage
    if coverage and not os.environ.get('FLASK_COVERAGE'):
        import sys
        os.environ['FLASK_COVERAGE'] = '1'
        os.execvp(sys.executable, [sys.executable] + sys.argv)

    print("**************Testing Started**********")
    # run the app in tesing configration
    app.config.from_object(config['testing'])
    config['testing'].init_app(app)
    # Remove the sqlite database files if exist
    for fl in glob.glob('data-test.sqlite'):
        os.remove(fl)
        print('old test sqlite database removed')

    deploy()  # redeploy the database
    fakedata()  # generate the fakedata

    import unittest
    tests = unittest.TestLoader().discover('tests')
    result = unittest.TextTestRunner(verbosity=2).run(tests).wasSuccessful()

    # generate test coverage report
    if COV:
        COV.stop()
        COV.save()
        print('Test Coverage Summary:')
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, 'tmp/coverage')
        COV.html_report(directory=covdir)
        print('HTML version: file://%s/index.html' % covdir)
        COV.erase()

    # the exit code is used for CircleCI
    import sys

    if result:  # tests passed
        sys.exit(0)
    else:  # tests failed
        sys.exit(1)


@manager.command
def profile(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


# run the db migration script
# this creates all tables when first run, after that
# if the database has no changes, nothing happens
@manager.command
def deploy():
    """Initialize the database and populate init data."""
    from flask_migrate import upgrade

    upgrade()  # upgrade to the latest db schema

    # setup necessary data to initialize database
    if Conference.query.filter_by(short_name='main').first():
        print('database already initialized')
    else:
        # add registration form questions
        FormConfiguration.insert_formConfiguration()
        Role.insert_roles()  # create user roles
        generate_main_conf()  # generate default main conference
        generate_admin()  # generate the site admin


# Caution!!!: this reset db migration and related sqlite files
# The name is designed on purpose to highlight the potential danger
@manager.command
def reset_db_danger():
    """Reset db migration and delete all related files."""
    from flask.ext.migrate import init, migrate
    # Remove the migration folder if exist
    if os.path.exists('migrations'):
        shutil.rmtree('migrations')

    # Remove the sqlite database files if exist
    for fl in glob.glob('*.sqlite'):
        os.remove(fl)

    # Reset Migration Database
    init()

    # migrate database to latest revision
    migrate(message='init')


@manager.command
def testconfs(email='harryjwang@gmail.com'):
    """Generate fake pending confs."""
    generate_fake_confs(10, email)  # create 10 pending conferences


@manager.command
def fakedata():
    """Generate fake testing data."""
    if User.query.filter_by(email='chair@conferency.com').first():
        print ('fake data already generated')
    else:
        generate_test_confs()  # load testing confs and tracks
        generate_fake_tickets()  # create fake tickets
        generate_test_users()  # create named fake users
        # generate_fake_users(100)  # create random users
        # add_self_follows()  # create self-follows for all users
        generate_fake_papers(100)  # create random papers
        generate_fake_reviews()  # create random reviews
        generate_fake_transactions()  # create fake tickets
        generate_fake_schedule()
        generate_default_addons()

if __name__ == '__main__':
    manager.run()
