"""Test Chair."""
import unittest
from flask import url_for
from app import create_app
from app.models import User

# this test case tests every page on the main manu
# simple check of 200 and 302


class AdminPagesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_admin_pages(self):

        # login with the chair account
        response = self.client.get(url_for('auth.login'))
        self.assertTrue(response.status_code == 200)
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)

        # set current conf to ICIS2015
        current_user = User.query.filter_by(
            email='chair@conferency.com').first()
        current_user.set_conference_id(2)
        # print current_user.curr_conf

        response = self.client.get('/conference/2/submission')
        self.assertTrue(
            response.status_code == 200, msg="All Submissions ICIS2015")

        response = self.client.get('/conference/2/submission_setting/form')
        self.assertTrue(
            response.status_code == 200, msg="Submission Form ICIS2015")

        response = self.client.get('/conference/2/submission_setting')
        self.assertTrue(
            response.status_code == 200, msg="Sumission Settings ICIS2015")

        response = self.client.get('/conference/2/review')
        self.assertTrue(
            response.status_code == 200, msg="All Reviews ICIS2015")

        response = self.client.get('/conference/2/review/assignment/manual')
        self.assertTrue(
            response.status_code == 200, msg="Review Assignment ICIS2015")

        response = self.client.get('/conference/2/review_request')
        self.assertTrue(
            response.status_code == 200, msg="Sub Review Request ICIS2015")

        response = self.client.get('/conference/2/review/decision')
        self.assertTrue(
            response.status_code == 200, msg="Review Decisions ICIS2015")

        response = self.client.get('conference/2/review_form')
        self.assertTrue(
            response.status_code == 200, msg="Review Form ICIS2015")

        # payment options
        response = self.client.get('/conference/2/review_setting')
        self.assertTrue(
            response.status_code == 200, msg="Review Settings ICIS2015")

        response = self.client.get('/conference/2/members')
        self.assertTrue(
            response.status_code == 200, msg="Conf Members ICIS2015")

        response = self.client.get('/conference/2/track_members')
        self.assertTrue(
            response.status_code == 200, msg="Track Members ICIS2015")

        response = self.client.get('/conference/2/conference_invitations')
        self.assertTrue(
            response.status_code == 200, msg="Conf Invitation ICIS2015")

        response = self.client.get('/conference/2/track_invitations')
        self.assertTrue(
            response.status_code == 200, msg="Track Invitations ICIS2015")

        response = self.client.get('/conference/2/notify/author')
        self.assertTrue(
            response.status_code == 200, msg="Contact Authors ICIS2015")

        response = self.client.get('/conference/2/notify/pc')
        self.assertTrue(
            response.status_code == 200, msg="Contact PC ICIS2015")

        response = self.client.get('/conference/2/notify/member')
        self.assertTrue(
            response.status_code == 200, msg="Contact All Members ICIS2015")

        response = self.client.get('/conference/2/tracks')
        self.assertTrue(
            response.status_code == 200, msg="Tracks ICIS2015")

        response = self.client.get('/conference/2/schedule')
        self.assertTrue(
            response.status_code == 200, msg="Schedule ICIS2015")

        response = self.client.get('/conference/2/setting')
        self.assertTrue(
            response.status_code == 200, msg="Settings ICIS2015")

        response = self.client.get('/conference/2/website')
        self.assertTrue(
            response.status_code == 200, msg="Website ICIS2015")

        response = self.client.get('/conference/2/proceedings')
        self.assertTrue(
            response.status_code == 200, msg="Proceedings ICIS2015")

        response = self.client.get('/conference/2/reports')
        self.assertTrue(
            response.status_code == 200, msg="Reports ICIS2015")

        response = self.client.get('/conference/2/log')
        self.assertTrue(
            response.status_code == 200, msg="Logs ICIS2015")

        # log out
        response = self.client.get(url_for('auth.logout'))
        self.assertTrue(response.status_code == 302)
