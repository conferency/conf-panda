import unittest
from flask import url_for
from app import create_app
from app.models import User

# this test case tests every page on the main manu
# simple check of 200 and 302


class MainPagesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_main_pages(self):

        # homepage
        response = self.client.get(url_for('auth.login'))
        self.assertTrue(response.status_code == 200, msg="Login")

        # set current conf to Main
        current_user = User.query.filter_by(
            email='chair@conferency.com').first()
        current_user.set_conference_id(1)
        # print current_user.curr_conf
        # print response.data

        # login with the chair account
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)

        # redirect to dashboard with Main conf selected
        self.assertTrue(
            b'All My Submissions' in response.data, msg="Dashboard Main")

        # my submissions page (main conf)
        response = self.client.get(url_for('submission.my_submissions'))
        self.assertTrue(response.status_code == 200, msg="My Submissions Main")

        # my reviews page (main conf)
        response = self.client.get(url_for('review.my_reviews'))
        self.assertTrue(response.status_code == 200, msg="My Reviews Main")

        # set current conf to ICIS2015
        current_user.set_conference_id(2)
        # print current_user.curr_conf

        response = self.client.get(url_for('main.dashboard'))
        self.assertTrue(response.status_code == 200, msg="Dashboard ICIS2015")

        # add submission page
        response = self.client.get(url_for('submission.add_submission'))
        self.assertTrue(
            response.status_code == 200, msg="Add Submission ICIS2015")

        # my submission page
        response = self.client.get(url_for('submission.my_submissions'))
        self.assertTrue(
            response.status_code == 200, msg="My Submissions ICIS2015")

        # my reviews page (icis2015)
        response = self.client.get(url_for('review.my_reviews'))
        self.assertTrue(response.status_code == 200, msg="My Reviews ICIS2015")

        # review preferences: need revision
        # response = self.client.get(url_for('conference.paper_biddings'))
        response = self.client.get('/conference/2/review_preferences')
        self.assertTrue(
            response.status_code == 200, msg="My Review Preferences ICIS2015")

        # my conferrences
        response = self.client.get(url_for('conference.my_conference'))
        self.assertTrue(
            response.status_code == 200, msg="My Conferences")

        # my registrations
        response = self.client.get(url_for('main.show_tickets'))
        self.assertTrue(
            response.status_code == 200, msg="My Registrations")

        # all conferences
        response = self.client.get(url_for('conference.all_conference'))
        self.assertTrue(
            response.status_code == 200, msg="All Conferences")

        # conference request
        response = self.client.get(url_for('conference.request_conference'))
        self.assertTrue(
            response.status_code == 200, msg="Request Conference")

        # my connections
        response = self.client.get('/followed-by/2')
        self.assertTrue(
            response.status_code == 200, msg="My Connections Chair User")

        # my connections
        response = self.client.get('/followed-by/2')
        self.assertTrue(
            response.status_code == 200, msg="My Connections Chair User")

        # conference request
        response = self.client.get(url_for('main.user_search'))
        self.assertTrue(
            response.status_code == 200, msg="User Directory")

        # sales summary
        response = self.client.get('/conference/2/registration_summary')
        self.assertTrue(
            response.status_code == 200, msg="Sales Summary ICIS2015")

        # orders
        response = self.client.get('/conference/2/registration_recent_orders')
        self.assertTrue(
            response.status_code == 200, msg="Orders ICIS2015")

        # registration form
        response = self.client.get('/conference/2/set_registration_form')
        self.assertTrue(
            response.status_code == 200, msg="Registration Form ICIS2015")

        # registration settings
        response = self.client.get('/conference/2/set_registration')
        self.assertTrue(
            response.status_code == 200, msg="Registration Settings ICIS2015")

        # payment options
        response = self.client.get('/conference/2/payment_options')
        self.assertTrue(
            response.status_code == 200, msg="Payment Options ICIS2015")

        # log out
        response = self.client.get(url_for('auth.logout'))
        self.assertTrue(response.status_code == 302)
