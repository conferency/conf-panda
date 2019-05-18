# -*- coding: utf-8 -*-
"""Data scheme for conferency."""

import hashlib
import os
import random
import string
import uuid
import sys
from collections import OrderedDict
from datetime import datetime, date
from itertools import groupby
import bleach
from flask import current_app, request, url_for, json
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, \
    BadSignature, SignatureExpired
# from markdown import markdown
from sqlalchemy import event, and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import column_property
from sqlalchemy.sql import func, select
from werkzeug.security import generate_password_hash, check_password_hash

# from . import APP_STATIC
from .__init__ import db, login_manager
from .__init__ import uploaded_papers
from .utils.exceptions import ValidationError
from .utils.customDataType import LowerCaseText, \
    NestedMutableJson as JsonObject

# from .utils.email_operation import send_email
from .utils.guid import GUID
from .utils.macros import generate_uuid
from .utils.stripeHelper import get_net, refund


# const
class Permission:
    MANAGE_PAPER = 0x01
    MANAGE_WEBSITE = 0x02
    MANAGE_REGISTRATION = 0x04
    MANAGE_REVIEW = 0x18
    MANAGE_INVITATION = 0x10
    MANAGE_TRACK = 0x20
    MANAGE_CONFERENCE = 0x80


class TicketStatus:
    NORMAL = 'Normal'
    DELETED = 'Deleted'


class PaperStatus:
    RECEIVED = 'Received'
    UNDER_REVIEW = 'Under Review'
    ACCEPTED = 'Accepted'
    REJECTED = 'Rejected'
    WITHDRAWN = 'Withdrawn'
    DELETED = 'Deleted'


class TransactionStatus:
    PENDING = 'Pending'
    CANCELLED = 'Cancelled'
    COMPLETED = 'Completed'
    REFUNDED = 'Refunded'


class InvitationStatus:
    PENDING = 'Pending'
    DECLINED = 'Declined'
    JOINED = 'Joined'
    REVOKED = 'Revoked'


class QuestionType:
    SING_CHOICE = 'SIN_CHOICE'
    MULT_CHOICE = 'MULT_CHOICE'
    SING_TEXT = 'SIN_TEXT'
    MULT_TEXT = 'MULT_TEXT'


class UserDocStatus:
    RECEIVED = 'Received'
    DELETED = 'Deleted'


# the following are the internal tables created to handle
# many to many relationships without custom fileds
paper_author = db.Table('paper_author',
                        db.Column('user_id', db.Integer,
                                  db.ForeignKey('users.id')),
                        db.Column('paper_id', db.Integer,
                                  db.ForeignKey('papers.id'))
                        )

paper_reviewer = db.Table('paper_reviewer',
                          db.Column('user_id', db.Integer,
                                    db.ForeignKey('users.id'),
                                    primary_key=True),
                          db.Column('paper_id', db.Integer,
                                    db.ForeignKey('papers.id'),
                                    primary_key=True)
                          )

discussant_paper_session = db.Table(
    'discussant_paper_session',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('paper_session_id',
              db.Integer,
              db.ForeignKey('paper_session.id')))


class AssociatedEmail(db.Model):
    __tablename__ = 'associated_emails'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    email = db.Column(LowerCaseText(128), unique=True, index=True)


class PaperBidding(db.Model):
    __tablename__ = 'paper_pc_bidding'
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    bid = db.Column(db.Integer)


class PaperSession(db.Model):
    """Associate table for papers and sessions."""

    __tablename__ = 'paper_session'
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'),
                         index=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'),
                           index=True)
    discussants = db.relationship('User', secondary=discussant_paper_session,
                                  backref=db.backref('paper_sessions',
                                                     lazy='dynamic'),
                                  lazy='dynamic')


class DelegateReview(db.Model):
    """Review delegation information."""

    __tablename__ = 'delegate_reviewers'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(64), default='Pending')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    email_content = db.Column(JsonObject, default={})
    delegator_id = db.Column(db.Integer, db.ForeignKey(
        'users.id'), index=True)
    delegatee_id = db.Column(db.Integer, db.ForeignKey(
        'users.id'))
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), index=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    review_id = db.Column(db.Integer, db.ForeignKey(
        'reviews.id'), nullable=True)
    message = db.Column(db.Text)

    def __repr__(self):
        return '<Review Delegate paper: %r, delegator: %r, delegatee: %r>' \
                % (self.paper.id, self.delegator.full_name,
                   self.delegatee.full_name)

    def __init__(self, **kwargs):
        """Init function."""
        super(DelegateReview, self).__init__(**kwargs)

    def is_revocable(self):
        """Check if delegation can be revoked."""
        if self.status == 'Pending':
            return True
        elif self.status == 'Accepted':
            return self.review_id is None
        else:
            return False

    def to_json_log(self):
        """Event log function."""
        json_review_delegation = {
            'Delegatee': self.delegatee.full_name,
            'Delegatee\'s email': self.delegatee.email,
            'Delegator': self.delegator.full_name,
            'Delegator\'s email': self.delegator.email,
            'Paper ID': self.paper_id,
            'Paper title': self.paper.title,
            'Message': self.message
        }
        return json_review_delegation

    def accept_subreview(self, delegatee_id):
        """Accept subreview."""
        if self.delegatee_id != delegatee_id:
            raise Exception('You are not the valid delegatee, please check if \
                the review request was sent to your email address.')
        paper = self.paper
        pc_role = Role.query.filter_by(name='Program Committee').first()
        if self.delegator not in paper.reviewers.all():
            raise Exception('The review request is not valid anymore')
        if not self.delegatee.is_joined_conference(self.conference):
            self.delegatee.join_conference(self.conference, pc_role)
        paper.reviewers.remove(self.delegator)
        paper.reviewers.append(self.delegatee)
        self.status = 'Accepted'
        db.session.add(self)
        db.session.add(paper)
        # self delegatee's current conference
        try:
            db.session.commit()
            self.delegatee.set_conference_id(paper.conference.id)
        except Exception:
            db.session.rollback()
            raise Exception('Operation failed, please try again or contact \
                            custom service')
        from .utils.event_log import add_event
        add_event(self.delegatee.full_name +
                  ' accepted the sub-review request',
                  self.to_json_log(),
                  conference_id=self.conference_id,
                  paper_id=self.paper_id,
                  type='subreview_accept')
        # send email to delegator

    def decline_subreview(self, message):
        """Decline subreview."""
        self.status = 'Declined'
        self.message = message
        db.session.add(self)
        db.session.commit()

        from .utils.event_log import add_event
        add_event(self.delegatee.full_name +
                  ' declined the sub-review request',
                  self.to_json_log(),
                  conference_id=self.conference_id,
                  paper_id=self.paper_id,
                  type='subreview_decline')
        # send email to delegator

    @staticmethod
    def add_subreview(delegator_id, delegatee_id, paper_id,
                      conference_id, email_content):
        """Add subreview."""
        delegation = DelegateReview(delegator_id=delegator_id,
                                    delegatee_id=delegatee_id,
                                    paper_id=paper_id,
                                    conference_id=conference_id,
                                    email_content=email_content)
        try:
            db.session.add(delegation)
            db.session.commit()
        except IntegrityError:
                db.session.rollback()
                return False
        from .utils.email_operation import send_email
        send_email(delegation.delegatee.email, email_content.get('subject'),
                   'email/review_delegate_notification',
                   reply_to=delegation.delegator.email,
                   content=email_content,
                   delegation_id=delegation.id)

        from .utils.event_log import add_event
        add_event(delegation.delegator.full_name +
                  ' delegated review assignment to ' +
                  delegation.delegatee.full_name,
                  delegation.to_json_log(),
                  conference_id=delegation.conference_id,
                  paper_id=delegation.paper_id,
                  type='subreview_new')
        # send notification to subreviewer
        return True


class ProductOptionSale(db.Model):
    __tablename__ = 'product_option_sale'
    product_option_id = db.Column('product_option_id', db.Integer,
                                  db.ForeignKey('product_options.id'),
                                  primary_key=True)
    ticket_transaction_id = db.Column('ticket_transaction_id', db.Integer,
                                      db.ForeignKey('ticket_transactions.id'),
                                      primary_key=True)
    quantity = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<ProductSale %r, %r>' % (self.product_option_id,
                                         self.ticket_transaction_id)


class JoinTrack(db.Model):
    __tablename__ = 'track_user'
    user_id = db.Column(db.Integer, db.ForeignKey(
        'users.id'), primary_key=True)
    track_id = db.Column(db.Integer, db.ForeignKey(
        'tracks.id'), primary_key=True)
    role_id = db.Column(db.Integer, db.ForeignKey(
        'roles.id'))
    registered = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    profile = db.Column(JsonObject, default={})
    manual_added = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<JoinTrack track_id: %r, role_id: %r, user_id: %r>' % (
            self.track_id, self.role_id, self.user_id)

    def __init__(self, **kwargs):
        super(JoinTrack, self).__init__(**kwargs)


class FavSession(db.Model):
    """Save favorite session."""

    __tablename__ = 'fav_sessions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                        primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'),
                           primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


# this is the many-to-many relationship for user following
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class FormConfiguration(db.Model):
    __tablename__ = 'form_configuration'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    configuration = db.Column(JsonObject, default={})
    common_questions = db.Column(JsonObject, default={})

    # payout_scheme = db.Column(db.PickleType)

    @staticmethod
    def insert_formConfiguration():
        # name, email, affiliation are in the form
        questions = OrderedDict({"2": {'require': False, 'include': False,
                                       'desc': 'Job Title', 'ques_type': 2,
                                       'options': []},
                                "3": {'require': True, 'include': True,
                                      'desc': 'Country', 'ques_type': 2,
                                      'options': []},
                                 "4": {'require': False, 'include': False,
                                       'desc': 'Phone', 'ques_type': 2,
                                       'options': []},
                                 "5": {'require': False, 'include': False,
                                       'desc': 'Website', 'ques_type': 2,
                                       'options': []}})
        configuration = OrderedDict({"1": {'desc': 'instruction',
                                           'item_type': 'textarea',
                                           'options': []}})
        formConfiguration = FormConfiguration(name='Common Form Configuration',
                                              configuration=configuration,
                                              common_questions=questions)
        db.session.add(formConfiguration)
        db.session.commit()

    # add new question in the common questions list
    def add_question(self, ques_type, desc, options,
                     include=True, require=True):
        new_question = {
            'type': ques_type,
            'desc': desc,
            'options': options,
            'include': include,
            'require': require
        }
        self.common_questions[generate_uuid()] = new_question
        db.session.add(self)
        db.session.commit()

    # add item in the configuration
    def add_item(self, item_type, desc, options):
        new_item = {
            'item_type': item_type,
            'desc': desc,
            'options': options
        }
        self.configuration[generate_uuid()] = new_item
        db.session.add(self)
        db.session.commit()


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    role_in_conference = db.relationship('JoinTrack', backref='role',
                                         lazy='dynamic',
                                         foreign_keys='JoinTrack.role_id')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.MANAGE_PAPER, False),
            'Registration Manager': (Permission.MANAGE_PAPER | Permission.MANAGE_REGISTRATION, False),
            'Track Chair': (Permission.MANAGE_PAPER | Permission.MANAGE_REVIEW | Permission.MANAGE_INVITATION, False),
            'Program Committee': (Permission.MANAGE_PAPER, False),
            'Author': (Permission.MANAGE_PAPER, True),
            'Chair': (Permission.MANAGE_PAPER | Permission.MANAGE_REVIEW | Permission.MANAGE_REGISTRATION |
                      Permission.MANAGE_WEBSITE | Permission.MANAGE_INVITATION | Permission.MANAGE_TRACK |
                      Permission.MANAGE_CONFERENCE, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()
        print("successfully inserted roles")

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    """User table."""

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(LowerCaseText(128), unique=True, index=True)
    country = db.Column(db.String(128))
    organization = db.Column(db.String(256))
    website = db.Column(db.String(256))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    # active = db.Column(db.Boolean, default=True)
    location = db.Column(db.String(128))
    state = db.Column(db.String(128))
    about_me = db.Column(db.Text)
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    avatar = db.Column(db.Text)
    tour_finished = db.Column(db.Boolean, default=False)
    primary_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    merged_users = db.relationship('User',
                                   backref=db.backref('primary_user',
                                                      remote_side=[id]),
                                   lazy='dynamic')
    curr_conf_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    reviews = db.relationship('Review', backref='reviewer', lazy='dynamic')
    # associated_emails = db.relationship(
    #     'AssociatedEmail', backref='user', lazy='dynamic')
    paper_biddings = db.relationship('PaperBidding',
                                     foreign_keys=[PaperBidding.user_id],
                                     backref=db.backref('user', lazy='joined'),
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    delegated_reviews = db.relationship('DelegateReview',
                                        foreign_keys=[
                                            DelegateReview.delegatee_id],
                                        backref=db.backref(
                                            'delegatee', lazy='joined'),
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')
    delegating_reviews = db.relationship('DelegateReview',
                                         foreign_keys=[
                                             DelegateReview.delegator_id],
                                         backref=db.backref(
                                             'delegator', lazy='joined'),
                                         lazy='dynamic',
                                         cascade='all, delete-orphan')
    delegating_papers = association_proxy('delegating_reviews', 'paper')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    invitations = db.relationship('Invitation', backref='inviter',
                                  lazy='dynamic',
                                  foreign_keys='Invitation.inviter_id')
    create_conferences = db.relationship(
        'Conference', backref='requester',
        lazy='dynamic', foreign_keys='Conference.requester_id')
    uploaded_files = db.relationship(
        'UserDoc', backref='author', lazy='dynamic')
    uploaded_papers = db.relationship(
        'Paper', backref='uploader', lazy='dynamic')
    tracks = db.relationship('JoinTrack',
                             foreign_keys=[JoinTrack.user_id],
                             backref=db.backref('member', lazy='joined'),
                             lazy='dynamic', cascade='all, delete-orphan')
    ticket_transactions = db.relationship(
        'TicketTransaction', backref='buyer', lazy='dynamic')
    todo_lists = db.relationship('Todo', backref='user', lazy='dynamic')
    event_logs = db.relationship('EventLog', backref='user', lazy='dynamic')
    email_templates = db.relationship(
        'EmailTemplate', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='receiver',
                                    lazy='dynamic',
                                    foreign_keys='Notification.receiver_id')
    send_notifications = db.relationship('Notification', backref='sender',
                                         lazy='dynamic',
                                         foreign_keys='Notification.sender_id')
    full_name = column_property(first_name + ' ' + last_name)
    review_comments = db.relationship('ReviewComment',
                                      backref='commenter', lazy='dynamic')
    fav_session_objs = db.relationship('FavSession',
                                       foreign_keys=[FavSession.user_id],
                                       backref=db.backref('user',
                                                          lazy='joined'),
                                       lazy='dynamic',
                                       cascade='all, delete-orphan')
    fav_sessions = association_proxy('fav_session_objs', 'session')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.followed.append(Follow(followed=self))
        # join the default conference for each user
        # self.tracks.append(JoinTrack(
        #     member=self, track=Conference.query.get(
        #         1).tracks.filter_by(default=True).first(),
        #     role=Role.query.filter_by(default=True).first()))
        self.curr_conf_id = 1
        # self.check_invitation()

    def __repr__(self):
        """Print user's id, name and email."""
        return u'<User {0} {1} {2} {3}>'.format(
                self.id, self.full_name, self.email,
                self.organization).encode('utf-8')

    @hybrid_property
    def nice_print(self):
        """Print user's id, name and email. Only used in jinja."""
        return u'<{0} {1} {2}>'.format(
                self.full_name, self.email,
                self.organization)

    def is_reviewer(self, paper):
        return self in paper.reviewers

    def review_assignment_conference(self, conference):
        return self.get_review_assignments.filter_by(
            conference_id=conference.id).all()

    def curr_conf_is_main(self):
        """Check if current_conf is main."""
        return self.curr_conf_id == 1

    def get_conference_role(self, conference):
        """Return role in conference."""
        return self.get_track_role(
            conference.tracks.filter_by(default=True).first())

    def has_role_in_track(self, conference):
        """Return True if user has role in tracks."""
        return len(JoinTrack.query.filter(JoinTrack.user_id == self.id,
                                          JoinTrack.track_id == Track.id,
                                          Track.conference_id == conference.id,
                                          Track.status == True,
                                          Track.default == False).all()) != 0

    def get_track_role(self, track):
        """Return role of the track."""
        join_track = JoinTrack.query.filter_by(track_id=track.id,
                                               user_id=self.id).first()
        if join_track:
            return join_track.role
        else:
            return None

    def can_join_conference(self, conference, check_joined=True):
        if check_joined:
            if self.is_joined_conference(conference):
                return False
        today = date.today()
        end = conference.end_date
        if today > end:
            return False
        return True

    def get_track_list(self, conference, include_default=True):
        """Return a list of ids of tracks which current user can control can be optimized."""
        track_list = []
        if self.is_chair(conference):
            if include_default:
                track_list = [
                    track.id for track in
                    conference.tracks.filter_by(status=True).all()]
            else:
                track_list = [
                    track.id for track in conference.tracks.filter(
                        Track.default == False,
                        Track.status == True).all()]
        else:
            # user is not a chair
            if include_default:
                tracks = conference.tracks.filter(Track.status == True).all()
            else:
                tracks = conference.tracks.filter(Track.default == False,
                                                  Track.status == True).all()
            for track in tracks:
                role = self.get_track_role(track)
                if role and role.name == 'Track Chair':
                    track_list.append(track.id)
                for subtrack in track.subtracks:
                    track_list.append(subtrack.id)
        return track_list

    def get_track_object_list(self, conference, include_default=True):
        r"""Return a list of object of tracks which current user can control can be optimized."""
        track_list = []
        if self.is_chair(conference):
            if include_default:
                track_list = [
                    track.id for track in conference.tracks.filter_by(status=True).all()]
            else:
                track_list = [track.id for track in conference.tracks.filter(Track.default == False,
                                                                             Track.status == True).all()]
        else:
            if include_default:
                tracks = conference.tracks.filter(
                    Track.status == True,
                    Track.parent_track_id == None).all()
            else:
                tracks = conference.tracks.filter(
                    Track.default == False,
                    Track.status == True,
                    Track.parent_track_id == None).all()
            for track in tracks:
                track_role = self.get_track_role(track)
                if track_role:
                    track_list.append(track)
                    # get id of subtracks
                    for subtrack in track.subtracks:
                        if subtrack.status:
                            track_list.append(subtrack)
        return track_list

    @hybrid_property
    def get_review_assignments(self):
        query_1 = Paper.query.filter(Paper.id == DelegateReview.paper_id,
                                     DelegateReview.delegator_id == self.id,
                                     or_(DelegateReview.status == 'Accepted',
                                         DelegateReview.status == 'Submitted',
                                         DelegateReview.status == 'Approved'))
        query_2 = self.papers_reviewed
        return query_1.union(query_2).filter(
                Paper.status != PaperStatus.WITHDRAWN,
                Paper.status != PaperStatus.DELETED)

    @hybrid_property
    def get_papers(self):
        """Return query on non deleted and withdrawn papers."""
        # return Paper.query.filter(Paper.status != PaperStatus.WITHDRAWN,
        #                           Paper.status != PaperStatus.DELETED,
        #                           paper_author.c.paper_id == Paper.id,
        #                           or_(paper_author.c.user_id == self.id,
        #                               Paper.uploader_id == self.id))
        return self.papers.filter(Paper.status != PaperStatus.WITHDRAWN,
                                  Paper.status != PaperStatus.DELETED)

    # following self in the init function
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()
        print("successfully added self follows for all users")

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    # @property
    # def avatar(self):
    #     if os.path.isfile(os.path.join(os.path.dirname(__file__),
    #                                    'static', 'upload', 'avatar',
    #                                    str(self.id) + '.png')):
    #         return url_for('static',
    #                        filename='upload/avatar/' + str(self.id) + '.png',
    #                        random=random.random(),
    #                        _external=True)
    #     else:
    #         return False

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        db.session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id, 'email': self.email})

    @staticmethod
    def reset_password(token, new_password):
        """Reset password."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception as e:
            raise e
        user = User.query.get(data.get('reset'))
        if user is None and user.email != data.get('email'):
            raise Exception('Cannot find user or valid email')
        user.password = new_password
        try:
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            raise e

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        db.session.commit()
        return True

    def generate_email_invitation_token(self, email, role, track_id,
                                        expiration=3600000):
        """Generate a token containing email and role."""
        # default expired in 40 days
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'email': email, 'role': role, 'track_id': track_id})

    @staticmethod
    def email_invitation(token):
        """Verify the token for email invitation."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except Exception:
            return False
        email = data.get('email')
        role = data.get('role')
        track_id = data.get('track_id')
        if (email and role and track_id) is None:
            return False
        else:
            return tuple((email, role, track_id))

    # This function determines what permissions a user has for a conf
    # the permission will be bonded with the default track of the conference
    def can(self, permissions, conference):
        """Check user's permission."""
        if self.is_administrator():
            # admin can do everything
            return True
        if self.is_joined_conference(conference):
            tracks = conference.tracks.filter_by(status=True).all()
            # need to be udpated will only check permissions on default track
            for track in tracks:
                join_track = self.tracks.filter_by(track_id=track.id).first()
                if join_track and (join_track.role.permissions & permissions == permissions):
                    return True
            return False
        else:
            return False

    # need to update
    def can_track(self, permissions, track):
        """Check permission on a track."""
        if self.is_administrator():
            # admin can do everything
            return True
        if track.default:
            return self.can(permissions, track.conference)
        join_track = self.tracks.filter_by(track_id=track.id).first()
        if join_track and \
                (join_track.role.permissions & permissions == permissions):
            return True
        else:
            return False

    @hybrid_property
    def conferences(self):
        """Return conferences which the user joined."""
        return Conference.query.filter(JoinTrack.user_id == self.id,
                                       JoinTrack.track_id == Track.id,
                                       Track.default == True,
                                       Track.conference_id == Conference.id).all()

    @conferences.expression
    def conferences(cls):
        """Return the SQL query that inquires conferences which the user joined."""
        return select([Conference]).where(and_(JoinTrack.user_id == cls.id,
                                               JoinTrack.track_id == Track.id,
                                               Conference.id == Track.conference_id,
                                               Track.status == True)).as_scalar()

    def is_chair(self, conference):
        """Return boolean indicating if the user is the chair of a conference."""
        return self.can(Permission.MANAGE_CONFERENCE, conference)

    def is_pc(self, conference):
        """Return boolean indicating if the user is the pc of a conference."""
        return len(JoinTrack.query.filter(
            JoinTrack.user_id == self.id,
            JoinTrack.role_id == Role.query.filter_by(
                name='Program Committee').first().id,
            JoinTrack.track_id == Track.id,
            Track.conference_id == conference.id).all()) != 0

    def is_administrator(self):
        """Check whether a user is conferency (Main conf) administrator."""
        def_track_id = Conference.query.filter_by(
            name='Main').first().tracks.filter_by(default=True).first().id
        admin_role_id = Role.query.filter_by(name="Administrator").first().id
        if self.tracks.filter_by(role_id=admin_role_id, track_id=def_track_id).first():
            return True
        else:
            return False

    def ping(self):
        """Slow query."""
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def follow(self, user):
        """Follow a user."""
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
            db.session.commit()
            # add notification
            Notification.add_notification(self, user, 'Social',
                                          'followed you.')
            # send email
            # send_email()

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
            db.session.commit()

    def is_following(self, user):
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    def is_joined_conference(self, conference):
        """Check if joined the conference."""
        return self.tracks.filter_by(
            track_id=conference.tracks.filter_by(
                default=True).first().id).first() is not None

    def is_registered(self, conference):
        default_track = self.tracks.filter_by(
            track_id=conference.tracks.filter_by(
                default=True).first().id).first()
        return default_track and default_track.registered

    def is_registered_track(self, track):
        jointrack = self.tracks.filter_by(track_id=track.id).first()
        return jointrack and jointrack.registered

    def register(self, conference):
        """Register for a conference."""
        join_track = self.tracks.filter_by(
            track_id=conference.tracks.filter_by(
                default=True).first().id).first()
        if join_track:
            join_track.registered = True
            db.session.add(join_track)
            db.session.commit()
        else:
            self.join_conference(conference, registered=True)

    def update_conference_role(self, conference, role):
        """Update user's role in a conference, or join a conference with assigned role if not join the conference yet.

        role cannot be empty.
        """
        join_track = JoinTrack.query.filter_by(
            user_id=self.id,
            track_id=conference.tracks.filter_by(default=True).first().id
            ).first()
        if join_track:
            join_track.role_id = role.id
            db.session.add(join_track)
            db.session.commit()
        else:
            self.join_conference(conference, role)

    def get_review_preference(self, conference):
        """Return review preference."""
        return ReviewPreference.query.filter_by(
            reviewer_id=self.id,
            conference_id=conference.id).first() or None

    def join_conference(self, conference, role=None, registered=False,
                        manual_added=False):
        r"""Users with a conference role are associated with default_track.

        Will override previous role if user joined the conference, so \
        use is_joined_conference function before join operation.
        For role of track chair, also need to let the user be track chair for \
        specific track.
        """
        if not role:
            role = Role.query.filter_by(default=True).first()
        join_track = JoinTrack(
            member=self,
            track_id=conference.tracks.filter_by(default=True).first().id,
            role_id=role.id,
            registered=registered,
            manual_added=manual_added)
        # add review preference for members
        review_preference = ReviewPreference.query.filter_by(
            reviewer_id=self.id, conference_id=conference.id).first()
        if not review_preference:
            review_preference = ReviewPreference(reviewer_id=self.id,
                                                 conference_id=conference.id)
            db.session.add(review_preference)
        try:
            db.session.add(join_track)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

    def leave_conference(self, conference):
        """Make a user leave a conference."""
        # change current conference
        if self.curr_conf_id == conference.id:
            self.curr_conf_id = Conference.query.filter_by(
                name='Main').first().id
            db.session.add(self)
        join_tracks = JoinTrack.query.filter(
            JoinTrack.user_id == self.id,
            JoinTrack.track_id == Track.id,
            Track.conference_id == conference.id).all()
        for jt in join_tracks:
            db.session.delete(jt)
        db.session.commit()

    def join_track(self, track, role=None):
        """User join a track. Will override previous if user already joined track."""
        if not role:
            role = Role.query.filter_by(default=True).first()
        self.leave_track(track)
        join_track = JoinTrack(member=self, track_id=track.id, role=role)
        db.session.add(join_track)
        db.session.commit()

    def is_joined_track(self, track):
        return self.tracks.filter_by(track_id=track.id).first() is not None

    def is_track_chair(self, track):
        if not self.is_joined_track(track):
            return False
        return self.tracks.filter_by(track_id=track.id).first().role.name == 'Track Chair'

    def leave_track(self, track):
        """User leaves a track."""
        join_track = self.tracks.filter_by(track_id=track.id).first()
        if join_track:
            db.session.delete(join_track)
        db.session.commit()

    def set_conference_id(self, conference_id):
        """Set current conference id for a user."""
        self.curr_conf_id = conference_id
        db.session.add(self)
        db.session.commit()

    def can_submit_paper(self, conference_id):
        """Check if user can submit paper."""
        try:
            submission_limit = int(self.curr_conf.configuration.get(
                'submission_limit', sys.maxsize))
        except Exception:
            submission_limit = sys.maxsize
        return len(
            self.papers.filter(
                Paper.conference_id == conference_id,
                Paper.status != PaperStatus.WITHDRAWN,
                Paper.status != PaperStatus.DELETED).all()) < submission_limit

    @hybrid_property
    def get_notifications(self):
        """Return query on non hide notifications."""
        return self.notifications.filter(Notification.status != 'Hide')

    @hybrid_property
    def get_notifications_dashboard(self):
        """Return query on non hide notifications."""
        return self.notifications.filter(Notification.status != 'Hide',
                                         Notification.seen == False)

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)

    def to_json(self):
        """Return user's info for private use."""
        papers = [paper.to_json() for paper in self.papers]
        reviews = [review.to_json() for review in self.reviews]
        followers = [
            one_follower.follower_id for one_follower in self.followers]
        followeds = [
            one_followed.followed_id for one_followed in self.followed]
        conferences = [
            conference.to_json() for conference in self.conferences
        ]
        json_user = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'city': self.location,
            'state': self.state,
            'country': self.country,
            'organization': self.organization,
            'website': self.website,
            'about_me': self.about_me,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'avatar': self.avatar,
            'papers': papers,
            'reviews': reviews,
            'followed': followeds,
            'followers': followers,
            'conferences': conferences
        }
        return json_user

    def user_info_json(self):
        """Return user's info for public use."""
        json_user = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'city': self.location,
            'state': self.state,
            'country': self.country,
            'organization': self.organization,
            'website': self.website,
            'about_me': self.about_me,
            'member_since': str(self.member_since),
            'last_seen': str(self.last_seen),
            'avatar': self.avatar
        }
        return json_user

    def get_conference_profile(self, conference):
        """Return conference profile."""
        if self.is_joined_conference(conference):
            json_user = self.user_info_json()
            json_user['conference_profile'] = self.tracks.filter(
                Track.conference_id == conference.id,
                Track.default == True).first().profile
            return json_user
        else:
            return False

    def set_conference_profile(self, conference, profile):
        """Return conference profile."""
        default_track = self.tracks.filter(
            Track.conference_id == conference.id,
            Track.default == True).first()
        if default_track:
            profile['id'] = self.id
            profile['email'] = self.email
            profile['avatar'] = default_track.profile.get('avatar', None)
            default_track.profile = profile
            try:
                db.session.add(default_track)
                db.session.commit()
                return True
            except Exception:
                db.session.rollback()
                return False
        else:
            return False

    def conference_profile_for_api(self, conference):
        default_track = self.tracks.filter(
            Track.conference_id == conference.id,
            Track.default == True).first()
        if default_track and \
            default_track.profile and \
                default_track.profile.get('use_conference_profile', False):
                return default_track.profile
        else:
            return self.user_info_json()

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        return User.query.get(data['id'])

    # generate password
    @staticmethod
    def generate_pwd():
        return ''.join(random.choice(string.ascii_uppercase +
                                     string.digits) for _ in range(8))


class AnonymousUser(AnonymousUserMixin):

    def can(self, permissions, conference):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
# very slow
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', user_id=self.author_id,
                              _external=True),
            'comments': url_for('api.get_post_comments', id=self.id,
                                _external=True),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i',
                        'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {'url': url_for('api.get_comment', id=self.id, _external=True),
                        'post': url_for('api.get_post', id=self.post_id, _external=True),
                        'body': self.body,
                        'body_html': self.body_html,
                        'timestamp': self.timestamp,
                        'author': url_for('api.get_user', user_id=self.author_id, _external=True),
                        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


# TODO maybe it doesnt make sense to separate this and "Paper"?
# Going to put this logic in paper for now


class UserDoc(db.Model):
    __tablename__ = 'user_documents'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'))
    status = db.Column(db.String(64), default=UserDocStatus.RECEIVED)

    # def __init__(self, **kwargs):
    #     super(UserDoc, self).__init__(**kwargs)
    #     if self.status is None:
    #         self.status = UserDocStatus.RECEIVED

    def __repr__(self):
        return '<UserDoc %r %r %r %r>' % (self.id, self.filename,
                                          str(self.timestamp),
                                          self.status)

    @property
    def imgsrc(self):
        return uploaded_papers.url(self.filename)


class Paper(db.Model):
    __tablename__ = 'papers'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.Text)  # TODO we dont want to use filename as PK
    files = db.relationship('UserDoc', backref='paper', lazy='dynamic')
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    submitted_time = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(64))
    title = db.Column(db.Text)
    abstract = db.Column(db.Text)
    keywords = db.Column(db.Text)
    submission_type = db.Column(db.Text)
    withdraw_reason = db.Column(db.Text)
    comment = db.Column(db.Text)
    proceeding_included = db.Column(db.Boolean, default=False)
    custom_question_answer = db.Column(JsonObject, default={})
    label = db.Column(db.Text)
    conference_id = db.Column(
        db.Integer, db.ForeignKey('conferences.id'), index=True)
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'))
    authors = db.relationship('User', secondary=paper_author,
                              backref=db.backref('papers', lazy='dynamic'),
                              lazy='dynamic')
    reviews = db.relationship('Review', backref='paper', lazy='dynamic')
    reviewers = db.relationship('User', secondary=paper_reviewer,
                                backref=db.backref('papers_reviewed',
                                                   lazy='dynamic'),
                                lazy='dynamic')
    delegated_review_assignment = db.relationship('DelegateReview',
                                                  foreign_keys=[
                                                      DelegateReview.paper_id],
                                                  backref=db.backref(
                                                      'paper', lazy='joined'),
                                                  lazy='dynamic',
                                                  cascade='all, delete-orphan')
    delegators = association_proxy('delegated_review_assignment', 'delegator')
    authors_list = db.relationship('Author', backref='paper', lazy='dynamic')
    paper_biddings = db.relationship('PaperBidding',
                                     foreign_keys=[PaperBidding.paper_id],
                                     backref=db.backref(
                                         'paper', lazy='joined'),
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
    sessions = db.relationship('PaperSession',
                               foreign_keys=[PaperSession.paper_id],
                               backref=db.backref('paper', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    event_logs = db.relationship('EventLog', backref='paper', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Paper, self).__init__(**kwargs)
        if self.status is None:
            self.status = PaperStatus.RECEIVED

    def __repr__(self):
        return '<Paper %r>' % self.title

    @property
    def imgsrc(self):
        return uploaded_papers.url(self.filename)

    @property
    def get_organizations(self):
        """Return organizations of authors."""
        organization_set = set()
        for author in self.authors:
            organization_set.add(author.organization)
        return organization_set

    @property
    def reviews_status(self):
        """Return a boolen to indicate if reviewers submitted review and reviewer."""
        review_status = []
        assigned_reviewers = self.reviewers.all()
        reviewed_reviewers = [review.reviewer for review in self.reviews.all()]
        for reviewer in assigned_reviewers:
            if reviewer in reviewed_reviewers:
                review_status.append((True, reviewer))
            else:
                review_status.append((False, reviewer))
        return review_status

    def is_reviewable(self):
        if self.track.configuration.get('allow_review_config'):
            return self.track.configuration.get('review_process', False)
        else:
            return self.conference.configuration.get('review_process', False)

    def if_show_author(self):
        if self.track.configuration.get('allow_review_config'):
            return not self.track.configuration.get('hide_author', False)
        else:
            return not self.conference.configuration.get('hide_author', False)

    # update function
    def record_updated_time(self):
        self.last_updated = datetime.utcnow()

    def get_bid(self, user):
        paper_bidding = self.paper_biddings.filter_by(user_id=user.id).first()
        if paper_bidding:
            return paper_bidding.bid
        else:
            return 1

    def to_json(self):
        authors = [author.to_json() for author in self.authors_list]
        reviews = [review.to_json() for review in self.reviews]
        json_paper = {
            'id': self.id,
            'url': url_for('api.get_paper', id=self.id, _external=True),
            'filename': self.filename,
            'uploader_id': self.uploader_id,
            'submitted_time': self.submitted_time.strftime('%x %X'),
            'last_updated': self.last_updated.strftime('%x %X'),
            'status': self.status,
            'authors': authors,
            'title': self.title,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'submission_type': self.submission_type,
            'reviews': reviews,
            'avg_score': self.avg_score,
            'conference_url': self.conference.website,
            'conference_name': self.conference.name,
            'conference_shortname': self.conference.short_name,
            'comment': self.comment,
            'label': self.label
        }

        return json_paper

    def to_json_log(self):
        authors = ''
        for author in self.authors_list.all():
            authors += '(' + str(author.id) + ') ' + author.full_name + '&emsp;'
        json_paper = {
            'Title': self.title,
            'Abstract': self.abstract,
            'Keywords': self.keywords,
            'Submission type': self.submission_type,
            'ID': self.id,
            # 'Url': url_for('api.get_paper', id=self.id, _external=True),
            'Filename': self.filename,
            'Uploader': '(' + str(self.uploader.id) + ') ' +
                        self.uploader.full_name,
            'Submitted time': self.submitted_time.strftime('%x %X'),
            'Last updated': self.last_updated.strftime('%x %X'),
            'Status': self.status,
            'Average score': self.avg_score,
            'Authors': authors,
            'Comment': self.comment,
        }

        return json_paper

    @hybrid_property
    def avg_score(self):
        if self.reviews.count():
            scores = []
            for review in self.reviews:
                scores.append(review.evaluation)
            return format(sum(scores) / float(len(scores)), '.1f')
        else:
            return 0

    @avg_score.expression
    def avg_score(cls):
        return select([func.avg(Review.evaluation).label('average')]).where(
            cls.id == Review.paper_id).as_scalar()

    def is_added_track(self, track):
        """Check whether a paper is in a track."""
        return self.track_id == track.id

    def add_to_track(self, track):
        """Join a paper to a track (also remove the paper from the old track).

        Also set the conf id as well."""
        conf = Conference.query.filter_by(id=track.conference_id).first()
        if not self.is_added_track(track):
            self.track_id = track.id
            self.conference_id = conf.id
            db.session.commit()

    def get_subreviewer(self, delegator):
        """Return sub reviewer."""
        delegation = self.get_delegation(delegator)
        if delegation:
            return delegation.delegatee
        else:
            return None

    def can_be_delegated(self, user):
        """Check if paper can be delegated by user."""
        # cannot be delegated if user is delegatee
        if self.conference.configuration.get('allow_pc_chair_delegation',
                                             False) and \
            self.if_has_review(user) is False and \
            (self.delegated_review_assignment.filter(
             DelegateReview.delegatee_id == user.id,
             DelegateReview.status == 'Accepted'
             ).first() is None) and \
            (user.is_pc(self.conference) or
             user.is_chair(self.conference)):
            return True
        else:
            return False

    def get_delegation(self, delegator):
        """Return delegation if user has delegated this paper to sub reviewer."""
        return self.delegated_review_assignment.filter(
            DelegateReview.delegator_id == delegator.id,
            DelegateReview.status != 'Declined',
            DelegateReview.status != 'Revoked').first()

    def if_has_subreview(self, delegator):
        """Check if user has delegated this paper to sub reviewer."""
        delegation = self.get_delegation(delegator)
        if delegation and delegation.review_id:
            return True
        else:
            return False

    def if_has_review(self, reviewer):
        """Check if user already submit a review for this paper."""
        return self.reviews.filter_by(
                reviewer_id=reviewer.id).first() is not None

    def is_editable(self, user):
        """Check if this paper is editable."""
        if self.status == PaperStatus.DELETED or \
                self.status == PaperStatus.REJECTED or \
                self.status == PaperStatus.WITHDRAWN:
            return False
        if user.is_chair(self.conference):
            return True
        elif self.uploader_id == user.id or self.authors.filter_by(
                id=user.id).first():
            if self.track.default is False and \
                    self.track.configuration.get('allow_submission_config'):
                configuration = self.track.configuration
            else:
                configuration = self.conference.configuration
            if configuration.get('submission_process') or \
                    (not configuration.get('submission_process') and
                        configuration.get('revision_submission')):
                    return True
            else:
                False
        else:
            return False

    def can_check_review(self):
        """Return boolean to indicate if authors can check reviews."""
        if self.status == 'Withdrawn' or self.status == 'Deleted':
            return False
        if self.track.allow_review_config():
            return self.track.configuration.get('show_reviews_author')
        else:
            return self.conference.configuration.get('show_reviews_author')

    def if_has_access(self, user):
        """Check if user has access to this paper."""
        # author, chair, discussant, moderator
        if user in self.authors or user.is_chair(self.conference) or \
            user.id == self.uploader_id or self.sessions.filter(
                or_(discussant_paper_session.c.user_id == user.id,
                    and_(PaperSession.session_id == Session.id,
                         moderator_session.c.session_id == Session.id,
                         moderator_session.c.user_id == user.id))).first():
            return True
        return False

    def is_downloadable(self, user):
        """Check if user can downlaod the paper."""
        # author, reviewer, chair, track chair, delegator,discussant, moderator
        if user.is_authenticated and (
            user in self.authors or user in self.reviewers or
            user.is_chair(self.conference) or
            user.is_track_chair(self.track) or user in self.delegators or
            self.sessions.filter(
                or_(discussant_paper_session.c.user_id == user.id,
                    and_(PaperSession.session_id == Session.id,
                         moderator_session.c.session_id == Session.id,
                         moderator_session.c.user_id == user.id))).first()):
            return True
        else:
            return False

    @hybrid_property
    def get_reviews(self):
        """Return query on active reviews."""
        return self.reviews

    def check_review_conflict(self, reviewer,
                              check_author=False,
                              check_reviewer=False):
        if check_author:
            authors = self.authors.all()
            # if author of the paper
            if reviewer in authors:
                return False, 'Author of this paper'
            if reviewer.organization in [
                    author.organization for author in authors]:
                return False, 'Same organization'
            paper_ids = []
            for author in authors:
                paper_ids += [
                    _paper.id for _paper in author.papers.filter(
                        Paper.status != PaperStatus.DELETED).all()]
            if db.session.query(paper_author).filter(
                    paper_author.c.user_id == reviewer.id,
                    paper_author.c.user_id.in_(paper_ids)).all():
                return False, 'Cooperated with authors'
        if check_reviewer:
            reviewers = self.reviewers.all()
            if reviewer in reviewers:
                return False, 'Reviewer of this paper'
        # check delegator
        delegation = DelegateReview.query.filter(
            DelegateReview.delegator_id == reviewer.id,
            DelegateReview.paper_id == self.id,
            DelegateReview.status == 'Accepted').first()
        if delegation:
            return False, 'Delegator of this paper'
        return True, None


@event.listens_for(Paper.reviewers, 'append')
def paper_reviewers_append(target, value, initiator):
    """Update review preference."""
    with db.session.no_autoflush:
        review_preference = ReviewPreference.query.filter_by(
            reviewer_id=value.id, conference_id=target.conference_id).first()
        review_preference.assigned_reviews_num += 1
        db.session.add(review_preference)


@event.listens_for(Paper.reviewers, 'remove')
def paper_reviewers_remove(target, value, initiator):
    """Update review preference."""
    with db.session.no_autoflush:
        review_preference = ReviewPreference.query.filter_by(
            reviewer_id=value.id, conference_id=target.conference_id).first()
        review_preference.assigned_reviews_num -= 1
        db.session.add(review_preference)


class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'))
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    evaluation = db.Column(db.Integer)
    confidence = db.Column(db.Integer)
    review_body = db.Column(db.Text)
    confidential_comments = db.Column(db.Text)
    custom_question_answer = db.Column(JsonObject, default={})
    update_timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.String(16), default='Submitted')
    comments = db.relationship(
        'ReviewComment', backref='review', lazy='dynamic')
    actions = db.relationship(
        'ReviewAction', backref='review', lazy='dynamic')
    # Generate fake reviews, default to 300

    def __repr__(self):
        return '<Review %r>' % self.id

    def __init__(self, **kwargs):
        # add a default track to conference
        super(Review, self).__init__(**kwargs)

    def to_json(self):

        json_review = {
            'review_id': self.id,
            'paper_id': self.paper_id,
            'reviewer_id': self.reviewer_id,
            'timestamp': self.timestamp.strftime('%x %X'),
            'evaluation': self.evaluation,
            'confidence': self.confidence,
            'review_body': self.review_body,
            'confidential_comments': self.confidential_comments,
            'custom_question_answer': self.custom_question_answer,
            'update_timestamp': self.update_timestamp.strftime('%x %X')
        }

        return json_review

    def to_json_log(self):
        custom_question_answer = ''
        for key, value in self.custom_question_answer.iteritems():
            custom_question_answer += '<p>' + \
                value['desc'] + ': ' + (value['answer'] if isinstance(value['answer'], unicode) else ', '.join(value['answer'])) + '</p>'
        json_review = {
            'Review ID': self.id,
            'Paper ID': self.paper_id,
            'Reviewer': self.reviewer.first_name + ' ' + self.reviewer.last_name,
            'Time': self.timestamp.strftime('%x %X'),
            'Evaluation': self.evaluation,
            'Confidence': self.confidence,
            'Review': self.review_body,
            'Confidential comments': self.confidential_comments,
            'Answers for Custom questions': custom_question_answer,
            'Update time': self.update_timestamp.strftime('%x %X')
        }

        return json_review

    def get_feedback_count(self, action_str):
        from sqlalchemy import func

        def get_count(q):
            # https://gist.github.com/hest/8798884
            count_q = q.statement.with_only_columns(
                [func.count()]).order_by(None)
            count = q.session.execute(count_q).scalar()
            return count
        return get_count(self.actions.filter_by(action=action_str))


class ReviewComment(db.Model):
    """Comments to a review"""

    __tablename__ = 'review_comments'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'))
    commenter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    text = db.Column(db.Text)


class ReviewAction(db.Model):
    """Thumb up or down to a review."""

    __tablename__ = 'review_actions'
    id = db.Column(db.Integer, primary_key=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'))
    commenter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    action = db.Column(db.Text)

    @staticmethod
    def add_review_rating(review_id, commenter_id, action, medium):
        """Add review rating."""
        review = Review.query.get(review_id)
        commenter = User.query.get(commenter_id)
        review_rating = ReviewAction(
            commenter_id=commenter_id,
            review_id=review_id,
            action=action
        )
        try:
            db.session.add(review_rating)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return False
        from .utils.event_log import add_event
        add_event(commenter.full_name + ' gave a feedback (' + action +
                  ') on a review for <a href="' +
                  url_for('paper.paper_reviews', paper_id=review.paper.id) +
                  '">paper ' + str(review.paper.id) + '</a>',
                  {'Feedback content': action, 'Medium': medium},
                  conference_id=review.conference_id,
                  paper_id=review.paper_id, review_id=review.id,
                  type='review_rating', override_user_id=commenter.id)
        return True


class Invitation(db.Model):
    """Invitation for joining conference or track."""

    __tablename__ = 'invitations'
    id = db.Column(db.Integer, primary_key=True)
    inviter_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    invitee_email = db.Column(LowerCaseText(128), index=True)
    invitee_first_name = db.Column(db.String(64))
    invitee_last_name = db.Column(db.String(64))
    invitee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    invitee_role = db.Column(db.String(64))
    invitee_status = db.Column(db.String(64), default=InvitationStatus.PENDING)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'))
    invitation_time = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    reaction_time = db.Column(db.DateTime, index=True, default=None)
    token = db.Column(db.Text)
    email_content = db.Column(JsonObject, default={})
    note = db.Column(db.Text)
    invitee_full_name = column_property(
        invitee_first_name + ' ' + invitee_last_name)

    def ping(self):
        """Invitation response time."""
        self.reaction_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def check_availablibity(self):
        """Only one ivitation can be pending."""
        if self.invitee_status != InvitationStatus.PENDING:
            return False
        else:
            return True

    def to_json_log(self):
        """Event log."""
        email_content = self.email_content
        json_invitation = {
            'Inviter id': self.inviter_id,
            'Invitee email': self.invitee_email,
            'Invitee first name': self.invitee_first_name,
            'Invitee last name': self.invitee_last_name,
            'Invitee role': self.invitee_role,
            'Invitee status': self.invitee_status,
            'Invitation sent': str(self.invitation_time),
            'Email subject': email_content.get('subject'),
            'Email content': email_content.get('content'),
            'Message': self.note
        }
        return json_invitation

    @staticmethod
    def add_invitation(inviter_id, invitee_email, invitee_first_name,
                       invitee_last_name, invitee_role, conference_id,
                       track_id, token, email_content):
        """Add invitation."""
        exist_user = User.query.filter_by(email=invitee_email).first()
        if exist_user and exist_user.primary_id:
            # send invitation to primary account
            exist_user = exist_user.primary_user
        # Track Program Committee is deprecated
        if invitee_role == 'Track Program Committee':
            invitee_role = 'Program Committee'
        invitation = Invitation(
            inviter_id=inviter_id,
            invitee_id=exist_user.id if exist_user else None,
            invitee_email=exist_user.email if exist_user else invitee_email,
            conference_id=conference_id,
            track_id=track_id,
            invitee_role=invitee_role,
            invitee_first_name=invitee_first_name,
            invitee_last_name=invitee_last_name,
            token=token,
            email_content=email_content)
        try:
            db.session.add(invitation)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return False
        from .utils.email_operation import send_email
        send_email(exist_user.email if exist_user else invitee_email,
                   email_content['subject'],
                   'email/custom_invitation',
                   content=email_content['content'],
                   reply_to=invitation.inviter.email,
                   conference=invitation.conference,
                   join_link=url_for('auth.invitation_register', token=token,
                                     _external=True),
                   decline_link=url_for('auth.invitation_decline', token=token,
                                        _external=True),
                   test_email=False)
        #
        from .utils.event_log import add_event
        add_event(
            invitation.inviter.full_name + ' invited ' +
            ((invitee_first_name + ' ' + invitee_last_name) if
                invitee_first_name else invitee_email) +
            ' to join the conference',
            invitation.to_json_log(),
            conference_id=conference_id,
            type='invitation_send')
        # send notification to existing user
        if exist_user:
            Notification.add_notification(
                invitation.inviter,
                exist_user,
                'invitation_send',
                invitation.inviter.full_name +
                ' invited you to join ' +
                invitation.conference.short_name.upper() +
                ' as ' + invitee_role,
                email_content['content'],
                [{
                    'type': 'button',
                    'class': 'btn-primary',
                    'text': 'Accept',
                    'url': url_for('api.accept_invitation', token=token)},
                 {
                    'type': 'button',
                    'class': 'btn-danger',
                    'text': 'Decline',
                    'url': url_for('api.decline_invitation', token=token)
                }])
        return True

    @staticmethod
    def validate_invitation(token, role, track_id):
        """Validate invitation.

        status cannot be accepted, declined or revoked.
        """
        invitation = Invitation.query.filter_by(token=token,
                                                invitee_role=role,
                                                track_id=track_id).first()
        if invitation is None:
            raise Exception('The invitation is invalid.')
        if invitation.invitee_status == InvitationStatus.JOINED:
            raise Exception('The invitation has been accepted.')
        elif invitation.invitee_status == InvitationStatus.DECLINED:
            raise Exception('The invitation has been declined.')
        elif invitation.invitee_status == InvitationStatus.REVOKED:
            raise Exception('The invitation has been revoked.')
        track = Track.query.filter_by(id=track_id, status=True).first()
        if track is None:
            raise Exception(
                'The track you are invited to join doesn\'t exist anymore.')
        return invitation

    def validate(self, user):
        """Check if the user is valid invitee."""
        return (self.invitee_id == user.id) or \
            (str(self.invitee_email) == str(user.email))

    def accept_invitation(self, user, note=''):
        """Accept invitation."""
        self.invitee_status = InvitationStatus.JOINED
        self.invitee_first_name = user.first_name
        self.invitee_last_name = user.last_name
        self.note = note
        self.invitee_id = user.id
        self.ping()
        db.session.add(self)
        assigned_role = Role.query.filter_by(
            name=self.invitee_role).first()
        invitation_track = Track.query.filter_by(
            id=self.track_id, status=True).first()
        if not user.is_joined_conference(self.conference):
            # user has not joined the conference
            if invitation_track.default:
                user.join_conference(self.conference, assigned_role)
            else:
                user.join_conference(self.conference)
                user.join_track(invitation_track, assigned_role)
        else:
            # user has joined the conference
            user.join_track(invitation_track, assigned_role)
        user.set_conference_id(self.conference_id)
        from .utils.email_operation import send_email
        send_email(user.email, 'Thank you for joining ' +
                   self.conference.short_name.upper(),
                   'email/invitation_accept_notification', user=user,
                   conference=self.conference)

        from .utils.event_log import add_event
        add_event(user.full_name + ' accepted the invitation',
                  self.to_json_log(),
                  conference_id=self.conference_id,
                  type='invitation_accept')
        # send email and notification to invitor and invitee
        # send_email(user.email, , template, test_email, reply_to)

    def decline_invitation(self, note=''):
        """Decline invitation."""
        self.invitee_status = InvitationStatus.DECLINED
        self.note = note
        db.session.add(self)
        self.ping()
        if self.invitee_id:
            name = User.query.get_or_404(self.invitee_id).full_name
        else:
            name = (self.invitee_first_name + ' ' + self.invitee_last_name) if self.invitee_first_name else self.invitee_email

        from .utils.event_log import add_event
        add_event(name + ' declined the invitation',
                  self.to_json_log(),
                  conference_id=self.conference_id,
                  type='invitation_decline')
        # send email and notification to invitor


# revoke the previous invitation
@event.listens_for(Invitation, 'init')
def invitation_init(target, args, kwargs):
    """The event is called before the actual __init__ constructor of the object
    is called. The pending invitation will be revoked.
    """
    invitation = Invitation.query.filter_by(
        track_id=kwargs.get('track_id'),
        invitee_email=kwargs.get('invitee_email'),
        invitee_status=InvitationStatus.PENDING).first()
    if invitation:
        invitation.invitee_status = InvitationStatus.REVOKED
        db.session.add(invitation)
        db.session.commit()
    else:
        pass


class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(LowerCaseText(128), index=True)
    country = db.Column(db.String(128))
    organization = db.Column(db.String(256))
    website = db.Column(db.String(256))
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'))
    full_name = column_property(first_name + " " + last_name)

    def to_json(self):
        json_author = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'full_name': self.full_name,
            'user_id': self.user_id,
            'url': url_for('main.user', id=self.user_id)
        }
        return json_author

    def is_registered_track(self, track):
        return bool(JoinTrack.query.filter_by(user_id=self.user_id, track_id=track.id, registered=True).first())


class Configuration(db.Model):
    __tablename__ = 'configurations'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64))
    value = db.Column(db.String(64))

    def to_json(self):
        json_configurations = {
            'key': self.key,
            'value': self.value,
        }

        return json_configurations


class Conference(db.Model):
    __tablename__ = 'conferences'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    short_name = db.Column(db.String(64), index=True)
    website = db.Column(db.Text)
    contact_email = db.Column(LowerCaseText(128))
    contact_phone = db.Column(db.String(64))
    address = db.Column(db.String(64))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    country = db.Column(db.String(128))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    timezone = db.Column(db.String(33))
    info = db.Column(db.Text)
    subjects = db.Column(db.Text)
    tags = db.Column(db.Text)
    featured = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(16), default='Pending')
    request_time = db.Column(db.DateTime, default=datetime.utcnow)
    # requester is the chair of conference
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    requester_info = db.Column(JsonObject, default={})
    approved_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    review_questions = db.Column(JsonObject, default={})
    submission_questions = db.Column(JsonObject, default={})
    configuration = db.Column(db.PickleType)
    review_deadline = db.Column(db.Date)
    submission_deadline = db.Column(db.Date)
    # Three plans: Free, Professional, Enterprise
    type = db.Column(db.String(32), default='Free')
    # relations
    tracks = db.relationship('Track', backref='conference', lazy='dynamic')
    papers = db.relationship('Paper', backref='conference', lazy='dynamic')
    reviews = db.relationship('Review', backref='conference', lazy='dynamic')
    invitations = db.relationship('Invitation', backref='conference',
                                  lazy='dynamic')
    email_templates = db.relationship(
        'EmailTemplate', backref='conference', lazy='dynamic')
    curr_conf_users = db.relationship('User', backref='curr_conf',
                                      lazy='dynamic',
                                      foreign_keys='User.curr_conf_id')
    registration = db.relationship(
        'Registration', backref='conference', uselist=False)
    site = db.relationship(
        'Website', backref='conference', uselist=False)
    todo_lists = db.relationship('Todo', backref='conference', lazy='dynamic')
    event_logs = db.relationship('EventLog', backref='conference',
                                 lazy='dynamic')
    conference_schedule = db.relationship('ConferenceSchedule',
                                          backref='conference',
                                          uselist=False)
    subreview_assignments = db.relationship('DelegateReview',
                                            backref='conference',
                                            lazy='dynamic')
    conference_payment = db.relationship(
        'ConferencePayment', backref='conference', uselist=False)

    def __repr__(self):
        return '<Conference %r>' % self.name

    def __init__(self, **kwargs):
        """Init for conference."""
        super(Conference, self).__init__(**kwargs)
        default_track = Track(name='Default', default=True)
        self.tracks.append(default_track)
        # db.session.add(default_track)
        if self.short_name != 'main':
            default_registration = Registration()
            self.registration = default_registration
            # db.session.add(default_registration)
            # default_website = Website(title=self.name)
            # self.site = default_website
            # db.session.add(default_website)
            default_schedule = ConferenceSchedule()
            self.conference_schedule = default_schedule
            # db.session.add(default_schedule)
            default_todo_list = Todo.conference_management_workflow()
            self.todo_lists.append(default_todo_list)
            # db.session.add(default_todo_list)
            self.configuration = {
                'review_process': True,
                'review_feedback': True,
                'allow_pc_chair_delegation': True,
                'hide_author': True,
                'hide_paper_status': True,
                'allow_edit_paper_author': False
            }
        else:
            default_todo_list = Todo(name='Main')
            self.todo_lists.append(default_todo_list)
            # db.session.add(default_todo_list)

    def to_json(self):
        tracks = []
        for track in self.tracks.filter(Track.status == True,
                                        Track.parent_track_id == None).all():
            tracks.append(track.to_json())
            for subtrack in track.subtracks:
                tracks.append(subtrack.to_json())

        json_conference = {
            'name': self.name,
            'short_name': self.short_name,
            'website': self.website,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
            'timezone': self.timezone,
            'info': self.info,
            'subjects': self.subjects,
            'tags': self.tags,
            'featured': self.featured,
            'status': self.status,
            'request_time': self.request_time,
            'requester_id': self.requester_id,
            'approved_time': self.approved_time,
            'approver_id': self.approver_id,
            'tracks': tracks,
            'review_questions': self.review_questions,
            'configuration': self.configuration
        }
        return json_conference

    @hybrid_property
    def members(self):
        """Return all members in this conference."""
        return User.query.filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id ==
            self.tracks.filter_by(default=True).first().id).all()

    def members_id_dict(self):
        return dict(User.query.with_entities(User.id, User.id).filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id ==
            self.tracks.filter_by(default=True).first().id).all())

    @hybrid_property
    def pcs(self):
        """Return all pc members in this conference."""
        track_ids = [
            track.id for track in self.tracks.filter_by(status=True).all()]
        pc_role = Role.query.filter_by(name='Program Committee').first()
        return User.query.filter(JoinTrack.user_id == User.id,
                                 JoinTrack.track_id.in_(track_ids),
                                 JoinTrack.role_id == pc_role.id).all()

    # @members.expression
    # def members(cls):
    #     return select

    @hybrid_property
    def chairs(self):
        """Return all chair members in this conference."""
        return User.query.filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id == self.tracks.filter_by(
                default=True).first().id,
            JoinTrack.role_id == Role.query.filter_by(
                name='Chair').first().id).all()

    @hybrid_property
    def track_chairs(self):
        track_ids = [
            track.id for track in self.tracks.filter_by(status=True).all()]
        role_ids = [
            role.id for role in Role.query.filter(
                Role.permissions >= 25, Role.permissions <= 191).all()]
        return User.query.filter(JoinTrack.user_id == User.id,
                                 JoinTrack.track_id.in_(track_ids),
                                 JoinTrack.role_id.in_(role_ids)).all()

    @hybrid_property
    def reviewers(self):
        track_ids = [
            track.id for track in self.tracks.filter_by(status=True).all()]
        role_ids = [
            role.id for role in Role.query.filter(or_(
                Role.name == 'Program Committee',
                Role.name == 'Chair',
                Role.name == 'Track Chair')).all()]
        return User.query.filter(
            JoinTrack.user_id == User.id,
            JoinTrack.track_id.in_(track_ids),
            JoinTrack.role_id.in_(role_ids)).order_by(User.first_name).all()

    @hybrid_property
    def get_tracks(self):
        """Return query on active non default tracks."""
        return self.tracks.filter_by(status=True, default=False)

    @hybrid_property
    def get_papers(self):
        """Return query on non deleted and withdrawn papers."""
        return self.papers.filter(Paper.status != PaperStatus.WITHDRAWN,
                                  Paper.status != PaperStatus.DELETED)

    def get_paper_by_id(self, paper_id):
        """Return a paper object."""
        return self.papers.filter(Paper.id == paper_id,
                                  Paper.status != PaperStatus.WITHDRAWN,
                                  Paper.status != PaperStatus.DELETED).first()

    def get_papers_status(self, status):
        """Return query on non deleted and withdrawn papers."""
        return self.papers.filter(Paper.status == status).all()

    def is_user_registered(self, user_id):
        """Deprecated."""
        default_track = self.tracks.filter_by(default=True).first().members\
            .filter_by(user_id=user_id).first()
        return default_track and default_track.registered

    def match_registration_record(self, user_id):
        """Find match registration."""
        user = User.query.get(user_id)
        if user:
            return User.query.filter(
                User.id == JoinTrack.user_id,
                JoinTrack.user_id != user_id,
                JoinTrack.track_id == self.tracks.filter_by(
                    default=True).first().id,
                JoinTrack.registered == True,
                User.first_name.like('%' + user.first_name + '%'),
                User.last_name.like('%' + user.last_name + '%')).all()
        else:
            []


class Track(db.Model):
    __tablename__ = 'tracks'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    parent_track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'))
    default = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.Boolean, default=True)
    configuration = db.Column(JsonObject, default={})
    subtracks = db.relationship('Track', backref=db.backref('parent_track',
                                                            remote_side=[id]))
    papers = db.relationship('Paper', backref='track', lazy='dynamic')
    members = db.relationship('JoinTrack',
                              foreign_keys=[JoinTrack.track_id],
                              backref=db.backref('track', lazy='joined'),
                              lazy='dynamic', cascade='all, delete-orphan')
    invitations = db.relationship('Invitation', backref='track',
                                  lazy='dynamic')

    def __init__(self, **kwargs):
        # add a default track to conference
        super(Track, self).__init__(**kwargs)

    @hybrid_property
    def track_chairs(self):
        return [JoinTrackItem.member for JoinTrackItem in
                self.members.filter_by(role_id=Role.query.filter_by(
                                       name='Track Chair').first().id).all()]

    def __repr__(self):
        return '<Track %r>' % self.name

    def to_json(self):
        json_track = {
            'id': self.id,
            'name': self.name,
            'conference_id': self.conference_id,
            'members': [{'role': member.role.name, 'id': member.member.id,
                         'name': member.member.full_name,
                         'email': member.member.email} for member in self.members],
            'num_of_paper': len(self.papers.all()),
            'default': self.default,
            'status': self.status,
            'subtracks': [subtrack.to_json() for subtrack in self.subtracks]
        }
        return json_track

    def is_deletable(self):
        """Check if the track is deletable."""
        if self.papers.filter(Paper.status != PaperStatus.WITHDRAWN).all() or \
                self.members.all():
            return False
        else:
            return True

    @hybrid_property
    def get_papers(self):
        """Return query on non deleted and withdrawn papers."""
        return self.papers.filter(Paper.status != PaperStatus.WITHDRAWN,
                                  Paper.status != PaperStatus.DELETED)

    def allow_submission_config(self):
        """Return allow_submission_config."""
        return self.configuration.get('allow_submission_config', False)

    def allow_review_config(self):
        """Return allow_review_config."""
        return self.configuration.get('allow_review_config', False)


class EmailTemplate(db.Model):
    __tablename__ = 'email_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    subject = db.Column(db.String(128))
    content = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # creator_id = db.Column(db.Integer)

    def __repr__(self):
        return '<Email Template %r>' % self.name

    def to_json(self):
        json_email_template = {
            'id': self.id,
            'name': self.name,
            'conference_id': self.conference_id,
            'subject': self.subject,
            'user_id': self.user_id,
            'content': self.content
        }
        return json_email_template


class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Boolean, default=False)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    tickets = db.relationship('Ticket', backref='registration', lazy='dynamic')
    promo_codes = db.relationship(
        'PromoCode', backref='registration', lazy='dynamic')
    products = db.relationship(
        'Product', backref='registration', lazy='dynamic')
    ticket_transactions = db.relationship(
        'TicketTransaction', backref='registration', lazy='dynamic')
    private_question = db.Column(JsonObject, default={})
    configuration_setting = db.Column(db.PickleType)
    payout = db.relationship(
        'Payout', backref='registration', uselist=False)

    def __repr__(self):
        return '<Registration conference_id %r>' % self.conference_id

    def __init__(self, **kwargs):
        super(Registration, self).__init__(**kwargs)
        self.configuration_setting = {'questions': []}
        self.private_question = OrderedDict()
        default_payout = Payout()
        self.payout = default_payout
        db.session.add(default_payout)

    @property
    def validate_questions(self):
        questions = []
        for k, v in self.private_question.items():
            if not v.get('deleted') and v['include']:
                v['id'] = k
                questions.append(v)
        return questions

    @hybrid_property
    def configuration(self):
        # include common configuration and private question
        configuration = OrderedDict()
        formConfiguration = FormConfiguration.query.filter_by(
            name='Common Form Configuration').first()  # get common questions
        # add common configuration in registration's configration
        for _id, configuration_item in formConfiguration.configuration.items():
            configuration[_id] = self.configuration_setting.get(_id, "")
        configuration['questions'] = self.configuration_setting['questions']
        # add common questions which are not in configuration_setting
        for _id, question in formConfiguration.common_questions.items():
            if not str(_id) in [str(q['id']) for q in configuration['questions']]:
                question['id'] = str(_id)
                configuration['questions'].append(question)
        return configuration

    @hybrid_property
    def get_tickets(self):
        return self.tickets.filter(Ticket.status != TicketStatus.DELETED)

    @hybrid_property
    def total_sold(self):
        """Return the total sale of tickets."""
        # ticket_ids = [ticket.id for ticket in self.get_tickets.all()]
        # ticket_prices = TicketPrice.query.filter(
        #     TicketPrice.id.in_(ticket_ids)).all()
        valid_ticket_transactions = self.get_ticket_transactions.order_by(
            TicketTransaction.currency).all()
        ticket_transactions_prices = groupby(
            valid_ticket_transactions,
            lambda t: t.currency)
        # print map(itemgetter(0), ticket_prices)
        # print map(itemgetter(1), ticket_prices)
        total_sold_prices = []
        for k, g in ticket_transactions_prices:
            total_sold_prices.append((k, sum(t.subtotal for t in list(g))))
        return total_sold_prices
        # valid_ticket_transactions = self.get_ticket_transactions.all()
        # if len(valid_ticket_transactions):
        #     total = 0
        #     for ticket_transaction in valid_ticket_transactions:
        #         total += ticket_transaction.subtotal
        #     return total
        # else:
        #     return 0.0

    @hybrid_property
    def net_sale(self):
        """Return the net sale of tickets."""
        valid_ticket_transactions = self.get_ticket_transactions.all()
        if len(valid_ticket_transactions):
            return sum(
                (t.amount * 0.97 - 1) if t.net > 0 else 0 for t in
                valid_ticket_transactions)
        else:
            return 0.0

    def get_sale_data(self):
        """Return total sale, net sale."""
        valid_ticket_transactions = self.get_ticket_transactions.order_by(
            TicketTransaction.currency).all()
        if len(valid_ticket_transactions):
            total_sold = 0
            net = 0
            ticket_transactions_prices = groupby(
                valid_ticket_transactions,
                lambda t: t.currency)
            total_sold_prices = []
            for key, group in ticket_transactions_prices:
                sum = 0
                for transaction in group:
                    total_sold += transaction.balance_transaction_amount
                    net += transaction.net
                    sum += transaction.subtotal
                total_sold_prices.append((key, sum))
            return {
                'total_sold': total_sold,
                'total_sold_detail': total_sold_prices,
                'net_sale': round(net, 2),
                'transaction_num': len(valid_ticket_transactions)
            }
        else:
            return {
                'total_sold': 0,
                'total_sold_detail': [],
                'net_sale': 0,
                'transaction_num': 0
            }
    # @total_sold.expression
    # def total_sold(cls):
    #     # wrong
    #     return select([func.sum((Ticket.number_of_sold * Ticket.price)).label('total')]).where(
    #         cls.id == Ticket.registration_id).as_scalar()

    @hybrid_property
    def total_sold_tickets(self):
        """Return the number of tickets sold."""
        valid_ticket_transactions = self.get_ticket_transactions.all()
        if len(valid_ticket_transactions):
            total = 0
            for ticket_transaction in valid_ticket_transactions:
                # need to be updated when transaction supports multiple tickets
                for ticket_sale in ticket_transaction.tickets.all():
                    total += ticket_sale.quantity
            return total
        else:
            return 0

    @hybrid_property
    def get_ticket_transactions(self, ):
        """Return completed transactions."""
        return self.ticket_transactions.filter_by(status='Completed')
        # def add_question(self, question):
        #     questions = pickle.loads(self.questions_schema)
        #     questions.append(question)
        #     self.questions_schema = pickle.dumps(questions)
        #     db.session.add(self)
        #     db.session.commit()

        # def delete_question(self, question):
        #     questions = pickle.loads(self.questions_schema)
        #     questions.remove(question)
        #     self.questions_schema = pickle.dumps(questions)
        #     db.session.add(self)
        #     db.session.commit()

    def get_products(self):
        """Return products."""
        return self.products.filter_by(status='Normal').all()


class TicketSale(db.Model):
    """Association table for ticket and ticket transaction."""

    __tablename__ = 'ticket_sales'
    ticket_id = db.Column('ticket_id', db.Integer,
                          db.ForeignKey('tickets.id'), primary_key=True)
    ticket_price_id = db.Column('ticket_price_id', db.Integer,
                                db.ForeignKey('ticket_prices.id'),
                                primary_key=True)
    ticket_transaction_id = db.Column('ticket_transaction_id',
                                      db.Integer,
                                      db.ForeignKey('ticket_transactions.id'),
                                      primary_key=True)
    quantity = db.Column(db.Integer)

    def __repr__(self):
        return '<TicketSale %r, %r>' % (self.ticket_id,
                                        self.ticket_transaction_id)


class TicketTransaction(db.Model):
    __tablename__ = 'ticket_transactions'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    status = db.Column(db.String(64))
    # payment info
    subtotal = db.Column(db.Float, default=0.0)
    net = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(8))
    card_number = db.Column(db.String(64))
    holder_name = db.Column(db.String(64))
    billing_street = db.Column(db.String(64))
    billing_city = db.Column(db.String(64))
    billing_state = db.Column(db.String(64))
    billing_country = db.Column(db.String(128))
    billing_zipcode = db.Column(db.String(8))
    billing_address = db.Column(db.String(128))
    security_code = db.Column(db.Integer)
    expiration_date = db.Column(db.String(7))
    attendee_info = db.Column(JsonObject, default={})
    charge_id = db.Column(db.String(128))
    balance_transaction_id = db.Column(db.String(128))
    balance_transaction_amount = db.Column(db.Float, default=0.0)
    refund_id = db.Column(db.String(128))
    refund_timestamp = db.Column(db.DateTime)
    ticket_sales = db.relationship(
        'TicketSale', foreign_keys=[TicketSale.ticket_transaction_id],
        backref=db.backref('ticket_transaction', lazy='joined'),
        lazy='select', cascade='all, delete-orphan')
    tickets = association_proxy('ticket_sales', 'ticket')
    product_options = db.relationship(
        'ProductOptionSale',
        foreign_keys=[ProductOptionSale.ticket_transaction_id],
        backref=db.backref('ticket_transaction', lazy='joined'),
        lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<TicketTransaction buyer_id %r>' % self.buyer_id

    # def __init__(self, **kwargs):
    #     super(TicketTransaction, self).__init__(**kwargs)
    #     if self.status is None:
    #         self.status = TransactionStatus.PENDING

    def add_ticket(self, ticket_price, qty):
        """Add ticket sale."""
        ticket_sales_obj = TicketSale(
            ticket_price_id=ticket_price.id,
            ticket_id=ticket_price.ticket.id,
            ticket_transaction_id=self.id,
            quantity=qty)
        # need to update
        # self.subtotal += ticket_price.amount
        self.currency = ticket_price.currency
        ticket_price.ticket.number_of_sold += qty
        ticket_price.number_of_sold += qty
        db.session.add(ticket_price)
        db.session.add(ticket_price.ticket)
        db.session.add(ticket_sales_obj)
        db.session.add(self)
        db.session.commit()

    def apply_promo_code(self, promo_code):
        self.promo_code_id = promo_code.id
        # if promo_code.type == 'percentage':
        #     self.subtotal *= (100 - promo_code.value) / 100.0
        # else:
        #     self.subtotal -= promo_code.value
        promo_code.usage += 1
        db.session.add(self)
        db.session.add(promo_code)
        db.session.commit()

    def add_product_option(self, product_option, qty):
        product_option_sale = ProductOptionSale(
            product_option_id=product_option.id,
            ticket_transaction_id=self.id,
            quantity=qty)
        product_option.number_of_sold += qty
        # self.subtotal += product_option.option_price
        # db.session.add(self)
        db.session.add(product_option_sale)
        db.session.add(product_option)
        db.session.commit()

    # this is for admin to help buyer update order
    def update_ticket(self, old_ticket, qty, new_ticket=None):
        ticket_sales_obj = self.tickets.filter_by(
            ticket_id=old_ticket.id).first()
        if not new_ticket:
            ticket_sales_obj.ticket_id = new_ticket.id
        ticket_sales_obj.quantity = qty
        db.session.add(ticket_sales_obj)
        db.session.commit()

    def update_status(self, status):
        self.status = status
        # update ticket#
        db.session.add(self)
        db.session.commit()

    def refund_transaction(self):
        if self.charge_id is None or self.charge_id == '0':
            raise Exception('Transaction has not been charged')
        if self.registration.payout.status == 'Completed':
            raise Exception(
                'Registration has been completed, please contact custom \
                service')
        try:
            self.refund_id = refund(self.charge_id)
            self.status = TransactionStatus.REFUNDED
            self.refund_timestamp = datetime.utcnow()
            # update ticket sale
            for ts in self.ticket_sales:
                ts.ticket_price.number_of_sold -= ts.quantity
                ts.ticket_price.ticket.number_of_sold -= ts.quantity
                db.session.add(ts.ticket_price)
                db.session.add(ts.ticket_price.ticket)
            # update product sale
            for ps in self.product_options:
                ps.product_option.number_of_sold -= ps.quantity
                db.session.add(ps.product_option)
            # update promo_code
            if self.promo_code_id:
                self.promo_code.usage -= 1
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e

    def to_json(self):
        json_ticket_transaction = {
            'id': self.id,
            'date': self.timestamp,
            'subtotal': self.subtotal,
            'status': self.status,
            'ticket_buyer': self.buyer_id,
            'attendee_info': self.attendee_info
        }
        return json_ticket_transaction

    def to_json_log(self):
        return {
            'Transaction id': self.id,
            'Attendee id': self.buyer_id,
            'Attendee': '%s %s' % (self.attendee_info['First Name'],
                                   self.attendee_info['Last Name']),
            'Attendee affiliation': self.attendee_info['Affiliation'],
            'Date': self.timestamp.strftime('%x %X'),
            'Status': self.status
        }


class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    name = db.Column(db.String(128))
    quantity = db.Column(db.Integer)
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(16), default=TicketStatus.NORMAL)
    number_of_sold = db.Column(db.Integer, default=0)
    price = db.Column(db.Float)
    prices = db.relationship(
        'TicketPrice', backref='ticket', lazy='dynamic')
    currencies = association_proxy('prices', 'currency')
    ticket_transactions = db.relationship('TicketSale',
                                          foreign_keys=[TicketSale.ticket_id],
                                          backref=db.backref(
                                              'ticket', lazy='joined'),
                                          lazy='dynamic',
                                          cascade='all, delete-orphan')

    def __repr__(self):
        return '<Ticket %r>' % self.name

    def __init__(self, **kwargs):
        super(Ticket, self).__init__(**kwargs)

    def to_json(self):
        json_ticket = {
            'id': self.id,
            'name': self.name,
            'price': str(self.price),
            'start_date': str(self.start_date),
            'end_date': str(self.end_date),
        }
        return json_ticket

    # @hybrid_property
    # def subtotal(self):
    #     if self.number_of_sold:
    #         return self.number_of_sold * self.price
    #     else:
    #         return 0
    #
    # @subtotal.expression
    # def subtotal(cls):
    #     return cls.number_of_sold * cls.price

    def add_price(self, currency, amount):
        """Add new price for ticket."""
        if currency in self.currencies:
            return False
        new_price = TicketPrice(currency=currency, amount=amount)
        self.prices.append(new_price)
        db.session.add(self)
        try:
            db.session.commit()
            return True
        except Exception:
            db.session.rollback()
            return False
    # add listeners to update number_of_sold

    # @event.listens_for(TicketSale, 'init')
    # def receive_init(target, args, kwargs):
    #     ticket = Ticket.query.get(kwargs['ticket_id'])
    #     ticket.number_of_sold += kwargs['quantity']
    #     db.session.add(ticket)
    # print target
    # print args
    # print kwargs


class TicketPrice(db.Model):
    __tablename__ = 'ticket_prices'
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(8), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    number_of_sold = db.Column(db.Integer, default=0)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id'))
    ticket_sales = db.relationship(
        'TicketSale', backref='ticket_price', lazy='dynamic')

    def __repr__(self):
        return '<Ticket Price %r %r %r>' % (self.ticket.name, self.currency,
                                            self.amount)

    def __str__(self):
        return "{} {}".format(self.currency, self.amount)

    def to_json(self):
        json_ticket_price = {
            'id': self.id,
            'currency': self.currency,
            'amount': self.amount,
            'ticket_id': self.ticket_id
        }
        return json_ticket_price


class PromoCode(db.Model):
    __tablename__ = 'promo_codes'
    id = db.Column(db.Integer, primary_key=True)
    promo_code = db.Column(db.String(128, collation='NOCASE'))
    type = db.Column(db.String(32))
    currency = db.Column(db.String(8))
    value = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    usage = db.Column(db.Integer, default=0)
    status = db.Column(db.String(16), default='Active')
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    ticket_transactions = db.relationship(
        'TicketTransaction', backref='promo_code', lazy='dynamic')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Promo Code %r>' % self.promo_code

    def __init__(self, **kwargs):
        super(PromoCode, self).__init__(**kwargs)

    def to_json(self):
        json_promo_codes = {
            'id': self.id,
            'promo_code': self.promo_code,
            'type': self.type,
            'value': self.value,
            'currency': self.currency,
            'quantity': self.quantity,
            'usage': self.usage,
            'status': self.status,
            'start_date': str(self.start_date),
            'end_date': str(self.end_date)
        }
        return json_promo_codes


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))
    inventory = db.Column(db.Integer)
    price = db.Column(db.Float)
    currency = db.Column(db.String(8))
    status = db.Column(db.String(16), default='Normal')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    require = db.Column(db.Boolean, default=False)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    options = db.relationship(
        'ProductOption', backref='product', lazy='dynamic')

    def __repr__(self):
        return '<Product %r>' % self.name

    def __init__(self, **kwargs):
        super(Product, self).__init__(**kwargs)
        default_product_option = ProductOption(
            option_name="Default",
            option_price=self.price,
            default=True,
            product_name=self.name)
        self.options.append(default_product_option)
        db.session.add(default_product_option)

    def to_json(self):
        json_product = {
            'id': self.id,
            'name': self.name,
            'inventory': self.inventory,
            'price': self.price,
            'status': self.status
        }
        return json_product


class ProductOption(db.Model):
    __tablename__ = 'product_options'
    id = db.Column(db.Integer, primary_key=True)
    option_name = db.Column(db.String(16))
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    product_name = db.Column(db.String(32))
    option_price = db.Column(db.Float)
    default = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.String(16), default='Normal')
    number_of_sold = db.Column(db.Integer, default=0)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    ticket_transactions = db.relationship(
        'ProductOptionSale',
        foreign_keys=[ProductOptionSale.product_option_id],
        backref=db.backref('product_option', lazy='joined'),
        lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return '<Product option %r>' % self.option_name

    def __init__(self, **kwargs):
        super(ProductOption, self).__init__(**kwargs)

    def to_json(self):
        json_product_option = {
            'id': self.id,
            'option_name': self.option_name,
            'option_price': self.option_price,
            'status': self.status,
            'currency': self.product.currency
        }
        return json_product_option


class Payout(db.Model):
    __tablename__ = 'payouts'
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(128))
    street_1 = db.Column(db.String(128))
    street_2 = db.Column(db.String(64))
    city = db.Column(db.String(64))
    state = db.Column(db.String(64))
    country = db.Column(db.String(128))
    zipcode = db.Column(db.String(8))
    payment_method = db.Column(db.String(16))
    bank_name = db.Column(db.String(128))
    account_type = db.Column(db.String(8))
    routing_number = db.Column(db.String(9))
    account_number = db.Column(db.String(32))
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'))
    status = db.Column(db.String(16), default='Pending')
    update_timestamp = db.Column(db.DateTime)
    payment_finish_timestamp = db.Column(db.DateTime)
    amount = db.Column(db.Float, default=0.0)
    note = db.Column(db.Text)

    def __repr__(self):
        return '<Payout %r>' % self.account_name

    def __init__(self, **kwargs):
        super(Payout, self).__init__(**kwargs)

        # @event.listens_for(TicketTransaction.status, 'set')
        # def receive_refund(target, value, oldvalue, initiator):
        #     print target
        #     print value
        #     print oldvalue
        #     print initiator
        #     target.tickets.all()[0].ticket.number_of_sold -= 1
        #     db.session.add(target)

        # class Question(db.Model):
        #     __tablename__ = 'tickets'
        #     id = db.Column(db.Integer, primary_key=True)
        #     question_type =
        #     desc =

        #     def __repr__(self):
        #         return '<Email Template %r>' % self.name


class Website(db.Model):
    __tablename__ = 'websites'
    id = db.Column(db.Integer, primary_key=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    title = db.Column(db.String(128))
    pages = db.relationship('Page', backref='website', lazy='dynamic')
    configuration = db.Column(JsonObject, default={})

    def __repr__(self):
        return '<Website %r>' % self.title

    def __init__(self, **kwargs):
        super(Website, self).__init__(**kwargs)
        index_page = Page(title='Index')
        self.pages.append(index_page)
        db.session.add(index_page)


class Page(db.Model):
    __tablename__ = 'pages'
    id = db.Column(db.Integer, primary_key=True)
    website_id = db.Column(db.Integer, db.ForeignKey('websites.id'))
    title = db.Column(db.String(128))
    content = db.Column(JsonObject, default={})

    def __repr__(self):
        return '<Page %r>' % self.title

    def __init__(self, **kwargs):
        super(Page, self).__init__(**kwargs)


class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    list = db.Column(JsonObject, default={})
    name = db.Column(db.String(64))

    def __repr__(self):
        return '<Todo list of %r>' % self.conference

    def __init__(self, **kwargs):
        super(Todo, self).__init__(**kwargs)

    @staticmethod
    def conference_management_workflow():
        todo = Todo(name='Conference Management Workflow')
        todo.list = OrderedDict()
        # with open(os.path.join(APP_STATIC, 'json/todo_list.json')) as data_file:
        #     data = json.load(data_file)
        # for item in data['Conference Management Workflow']:
        #     todo.list[generate_uuid()] = item
        return todo


class EventLog(db.Model):
    """Event log."""

    __tablename__ = 'event_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'))
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'))
    event = db.Column(JsonObject, default={})
    type = db.Column(db.String(64))


class ConferenceSchedule(db.Model):
    """Schedule for conference."""

    __tablename__ = 'conference_schedules'
    id = db.Column(db.Integer, primary_key=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    publish = db.Column(db.Boolean, default=False)
    sessions = db.relationship('Session',
                               backref='conference_schedule',
                               lazy='dynamic')

    # def schedule_info(self):
    #     conference = self.conference_id
    #     schedule_json = {
    #         title
    #     }
    #     pass

    @hybrid_property
    def get_sessions(self):
        """Return query on non deleted sessions."""
        return self.sessions.filter(Session.status != 'Deleted').order_by(
            Session.start_time.asc())


speaker_session = db.Table('speaker_session',
                           db.Column('user_id', db.Integer,
                                     db.ForeignKey('users.id')),
                           db.Column('session_id', db.Integer,
                                     db.ForeignKey('sessions.id'))
                           )


moderator_session = db.Table('moderator_session',
                             db.Column('user_id', db.Integer,
                                       db.ForeignKey('users.id')),
                             db.Column('session_id', db.Integer,
                                       db.ForeignKey('sessions.id'))
                             )


class Session(db.Model):
    """Session for schedule."""

    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True)
    conference_schedule_id = db.Column(db.Integer,
                                       db.ForeignKey(
                                            'conference_schedules.id'))
    venue = db.Column(db.String(128))
    type = db.Column(db.String(128))
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    title = db.Column(db.Text)
    description = db.Column(db.Text)
    status = db.Column(db.String(64), default='Normal')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    speakers = db.relationship('User', secondary=speaker_session,
                               backref=db.backref('speak_sessions',
                                                  lazy='dynamic'),
                               lazy='dynamic')
    moderators = db.relationship('User', secondary=moderator_session,
                                 backref=db.backref('moderator_sessions',
                                                    lazy='dynamic'),
                                 lazy='dynamic')
    paper_sessions = db.relationship('PaperSession',
                                     foreign_keys=[PaperSession.session_id],
                                     backref=db.backref('session',
                                                        lazy='joined'),
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
    papers = association_proxy('paper_sessions', 'paper')
    fav_sessions = db.relationship('FavSession',
                                   foreign_keys=[FavSession.session_id],
                                   backref=db.backref('session',
                                                      lazy='joined'),
                                   lazy='dynamic',
                                   cascade='all, delete-orphan')

    def __repr__(self):
        """Return description of the session."""
        return '<Session id %r>' % self.id

    def to_json(self):
        """Return json of the session."""
        json_session = {
            'id': self.id,
            'title': self.title,
            'venue': self.venue,
            'type': self.type,
            'description': self.description,
            'start_time': str(self.start_time)[:16],
            'end_time': str(self.end_time)[:16],
        }
        conference = self.conference_schedule.conference
        if self.type != 'regular':
            json_session['speakers'] = [
                speaker.conference_profile_for_api(
                    conference) for speaker in self.speakers]
            json_session['moderators'] = [
                moderator.conference_profile_for_api(
                    conference) for moderator in self.moderators]
            if self.type == 'paper':
                json_session['papers'] = [
                    {
                        'id': paper_session.paper.id,
                        'title': paper_session.paper.title,
                        'abstract': paper_session.paper.abstract,
                        'label': paper_session.paper.label,
                        'authors': [
                            {
                                'first_name': author.first_name,
                                'last_name': author.last_name,
                                'email': author.email,
                                'organization': author.organization,
                                'website': author.website,
                                # 'avatar': author.avatar,
                                # 'about_me': author.about_me
                            } for author in paper_session.paper.authors_list],
                        'discussants': [
                            discussant.conference_profile_for_api(
                                conference) for discussant in
                            paper_session.discussants]
                    } for paper_session in self.paper_sessions]
        return json_session


class Notification(db.Model):
    """Notifications."""

    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    type = db.Column(db.String(64))
    display = db.Column(JsonObject, default={})
    seen = db.Column(db.Boolean, default=False, index=True)
    status = db.Column(db.String(64), default='Unread')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    @staticmethod
    def add_notification(sender, receiver, type, headline='', content='',
                         html_element=''):
        """Add a notification."""
        notification = Notification(sender_id=sender.id,
                                    receiver_id=receiver.id,
                                    type=type,
                                    display={
                                        'headline': headline,
                                        'content': content,
                                        'html_element': html_element
                                    })
        try:
            db.session.add(notification)
            db.session.commit()
            return True
        except IntegrityError:
            db.session.rollback()
            return False


class ReviewPreference(db.Model):
    """Review preferences for user."""

    __tablename__ = 'review_preferences'
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    assigned_reviews_num = db.Column(db.Integer, default=0)
    assigned_reviews_max = db.Column(db.Integer, default=3)
    preferred_keywords = db.Column(db.Text, default='')
    rejected_keywords = db.Column(db.Text, default='')

    @hybrid_property
    def accept_assignment(self):
        return self.assigned_reviews_max > self.assigned_reviews_num

    @accept_assignment.expression
    def accept_assignment(cls):
        return cls.assigned_reviews_max > cls.assigned_reviews_num


class RequestLog(db.Model):
    """Record users' activities."""

    __tablename__ = 'request_logs'
    id = db.Column(GUID(), default=uuid.uuid4, primary_key=True,
                   autoincrement=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    # real_user_id should be empty if user is not masqueraded
    real_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    url = db.Column(db.Text)
    is_xhr = db.Column(db.Boolean)
    blueprint_name = db.Column(db.String(32))
    function_name = db.Column(db.String(128))
    view_args = db.Column(JsonObject, default={})
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(256))
    remote_ip = db.Column(db.String(256))
    user_agent = db.Column(db.Text)
    http_method = db.Column(db.String(16))
    http_status = db.Column(db.Integer)
    http_version = db.Column(db.String(32))
    interaction_milli = db.Column(db.Integer)
    query_string = db.Column(db.Text)
    browser = db.Column(db.String(32))

    @staticmethod
    def add_request_log(url, is_xhr, blueprint_name, function_name, view_args,
                        remote_ip, user_agent, browser, http_method,
                        http_status, http_version, interaction_milli,
                        query_string, session_id=None, user_id=None,
                        real_user_id=None, conference_id=None):
        """Add new request log."""
        request_log = RequestLog(url=url,
                                 is_xhr=is_xhr,
                                 view_args=view_args,
                                 blueprint_name=blueprint_name,
                                 function_name=function_name,
                                 session_id=session_id,
                                 remote_ip=remote_ip,
                                 user_agent=user_agent,
                                 browser=browser,
                                 http_method=http_method,
                                 http_status=http_status,
                                 http_version=http_version,
                                 user_id=user_id, real_user_id=real_user_id,
                                 conference_id=conference_id,
                                 interaction_milli=interaction_milli,
                                 query_string=query_string)
        return request_log


class ConferencePayment(db.Model):
    """Payment info for conferences."""

    __tablename__ = 'conference_payments'
    id = db.Column(db.Integer, primary_key=True)
    conference_id = db.Column(db.Integer, db.ForeignKey('conferences.id'))
    stripe_customer_id = db.Column(db.Text)
    card_info = db.Column(JsonObject, default={})
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, default=0.0)
    charged = db.Column(db.Float, default=0.0)
    # balance = db.Column(db.Float, default=0.0)
    transactions = db.relationship('ConferenceTransaction',
                                   backref='conference_payment',
                                   lazy='dynamic')

    @hybrid_property
    def balance(self):
        return self.charged - self.total

    @balance.expression
    def balance(cls):
        return cls.charged - cls.total

    def add_transaction(self, payer_id, charge_id, balance_transaction_id,
                        addon_id, promo_code_id, amount):
        """Add transaction."""
        conf_trans = ConferenceTransaction(
            payer_id=payer_id,
            charge_id=charge_id,
            balance_transaction_id=balance_transaction_id,
            net=get_net(balance_transaction_id)[0],
            promo_code_id=promo_code_id,
            amount=amount)
        addon = ConferenceAddon.query.get(addon_id)
        if addon:
            conf_trans.addons.append(addon)
            addon.num_sold += addon.num_sold + 1
        self.transactions.append(conf_trans)
        try:
            db.session.add(addon)
            db.session.add(conf_trans)
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            raise e

    def last_credit_card(self):
        if self.stripe_customer_id:
            return self.card_info[next(reversed(self.card_info))]
        else:
            return None


transaction_addon = db.Table(
    'transaction_addon',
    db.Column('transaction_id', db.Integer,
              db.ForeignKey('conference_transactions.id'), primary_key=True),
    db.Column('addon_id', db.Integer,
              db.ForeignKey('conference_addons.id'), primary_key=True))


class ConferenceAddon(db.Model):
    """Conference addons."""

    __tablename__ = 'conference_addons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    num_sold = db.Column(db.Integer, default=0)
    status = db.Column(db.String(32), default='Normal')
    price = db.Column(db.Float, default=0.0)


class ConferenceTransaction(db.Model):
    """Conference transactions."""

    __tablename__ = 'conference_transactions'
    id = db.Column(db.Integer, primary_key=True)
    conference_payment_id = db.Column(
        db.Integer, db.ForeignKey('conference_payments.id'))
    payer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(64), default='Completed')
    charge_id = db.Column(db.Text)
    refund_id = db.Column(db.Text)
    balance_transaction_id = db.Column(db.String(128))
    charge_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    refund_timestamp = db.Column(db.DateTime)
    amount = db.Column(db.Float, default=0.0)
    net = db.Column(db.Float, default=0.0)
    promo_code_id = db.Column(
        db.Integer, db.ForeignKey('conference_promo_codes.id'))
    addons = db.relationship(
        'ConferenceAddon',
        secondary=transaction_addon,
        backref=db.backref('transactions', lazy='dynamic'),
        lazy='dynamic')

    def refund_transaction(self):
        """Make a refund."""
        if self.charge_id:
            try:
                self.refund_id = refund(self.charge_id)
                self.status = TransactionStatus.REFUNDED
                self.refund_timestamp = datetime.utcnow()
                # send email
                db.session.add(self)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                raise e
        else:
            pass


class ConferencePromoCode(db.Model):
    __tablename__ = 'conference_promo_codes'
    id = db.Column(db.Integer, primary_key=True)
    promo_code = db.Column(db.String(128))
    type = db.Column(db.String(32))
    value = db.Column(db.Float)
    quantity = db.Column(db.Integer)
    usage = db.Column(db.Integer, default=0)
    status = db.Column(db.String(16), default='Active')
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date)
    conference_transactions = db.relationship(
        'ConferenceTransaction', backref='promo_code', lazy='dynamic')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Conference Promo Code %r>' % self.promo_code

    def __init__(self, **kwargs):
        super(ConferencePromoCode, self).__init__(**kwargs)

    def to_json(self):
        json_promo_codes = {
            'id': self.id,
            'promo_code': self.promo_code,
            'type': self.type,
            'value': self.value,
            'quantity': self.quantity,
            'usage': self.usage,
            'status': self.status,
            'start_date': str(self.start_date),
            'end_date': str(self.end_date)
        }
        return json_promo_codes

    @staticmethod
    def validate_promo_code(promo_code):
        """Validate promo code."""
        today = datetime.now().date()
        promo_code = ConferencePromoCode.query.filter(
            ConferencePromoCode.promo_code == promo_code,
            ConferencePromoCode.status == 'Active',
            ConferencePromoCode.start_date <= today,
            ConferencePromoCode.end_date >= today
        ).first()
        if promo_code:
            return promo_code
        else:
            return None
