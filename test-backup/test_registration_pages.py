import unittest
from flask import url_for
from app import create_app
from app.models import User

# this test case tests every page on the main manu
# simple check of 200 and 302


class RegistrationPagesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_registration_pages(self):

        # login with the chair account
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)

        # set current conf to ICIS2015
        current_user = User.query.filter_by(
            email='chair@conferency.com').first()
        current_user.set_conference_id(2)
        # print current_user.curr_conf

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
