# -*- coding: utf-8 -*-
"""Test review delegation."""
import unittest
from flask import url_for
from app import create_app, db
from app.models import User, Paper, DelegateReview

delegate_1 = {
    'firstname': 'Eddi',
    'lastname': 'Huang',
    'email': 'leonfeng@conferency.com',
    'subject': 'review delegation test',
    'content': 'Dear *FIRST_NAME*, <p>I am a PC member of *CONFERENCE_NAME*. \
    Could you please write a review for me on the following paper: </p>\
    ------------------------------------- <br> \
    Title: *TITLE* <br> \
    ------------------------------------- <br> \
    <p>I need to receive the review by \
    The instructions on how to answer this review request can be found at the \
    bottom of this message. <p> \
    Best regards, <br> \
    Kevin Durant <pc@conferency.com>'
}

delegate_2 = {
    'firstname': 'Eddi',
    'lastname': 'Huang',
    'email': 'leonfeng@conferency.com',
    'subject': 'review delegation test',
    'content': 'Dear *FIRST_NAME*, <p>I am a PC member of *CONFERENCE_NAME*. \
    Could you please write a review for me on the following paper: </p>\
    ------------------------------------- <br> \
    Title: *TITLE* <br> \
    ------------------------------------- <br> \
    <p>I need to receive the review by \
    The instructions on how to answer this review request can be found at the \
    bottom of this message. <p> \
    Best regards, <br> \
    Kevin Durant <pc@conferency.com>'
}

class ReviewDelegationTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test1_pc_review_delegate(self):
        # login first
        response = self.client.post(url_for('auth.login'), data={
            'email': 'pc@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        # get two assignment
        pc = User.query.filter_by(email='pc@conferency.com').first()
        pc.set_conference_id(2)
        paper_1 = Paper.query.filter(Paper.conference_id == 2,
                                     ~Paper.reviewers.contains(pc)).first()
        paper_1.reviewers.append(pc)
        db.session.add(paper_1)
        db.session.commit()
        paper_2 = Paper.query.filter(Paper.conference_id == 2,
                                     ~Paper.reviewers.contains(pc)).first()
        paper_2.reviewers.append(pc)
        db.session.add(paper_2)
        db.session.commit()
        # delegate review to new user
        response = self.client.post(
            url_for('review.review_request', paper_id=paper_1.id),
            data=delegate_1,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Review request is sent' in data)
        response = self.client.post(
            url_for('review.review_request', paper_id=paper_2.id),
            data=delegate_2,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Review request is sent' in data)

    def test2_accept_delegation(self):
        # get the delegation id
        delegator = User.query.filter_by(email='pc@conferency.com').first()
        delegatee = User.query.filter_by(
            email='leonfeng@conferency.com').first()
        delegatee.password = 'test'
        db.session.add(delegatee)
        db.session.commit()
        delegation = DelegateReview.query.filter_by(
            delegatee_id=delegatee.id,
            delegator_id=delegator.id,
            status='Pending').first()
        response = self.client.post(
            url_for('auth.login', delegation_id=delegation.id),
            data={
                'email': 'leonfeng@conferency.com',
                'password': 'test'
            },
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Thank you for accepting this reivew request' in data)

    def test3_decline_delegation(self):
        delegator = User.query.filter_by(email='pc@conferency.com').first()
        delegatee = User.query.filter_by(
            email='leonfeng@conferency.com').first()
        delegation = DelegateReview.query.filter_by(
            delegatee_id=delegatee.id,
            delegator_id=delegator.id,
            status='Pending').first()
        response = self.client.post(
            url_for('auth.review_request_operation',
                    delegation_id=delegation.id,
                    operation='decline'),
            data={
                'email': 'leonfeng@conferency.com',
                'note': 'Bye bye Bye bye Bye bye Bye bye'
            },
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue(
            'Thank you, delegator will receive your message.' in data)
