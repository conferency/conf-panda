# -*- coding: utf-8 -*-
import json
import unittest
from base64 import b64encode

from flask import url_for

from app import create_app


class ConferenceRequestsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)
        self.conf_id = 6

    def tearDown(self):
        self.app_context.pop()

    def get_api_headers(self, username, password):
        return {
            'Authorization': 'Basic ' + b64encode(
                (username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test_conference_upgrade_payment(self):

        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            # declined case
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            response = c.get(url_for('conference.payment', conference_id=self.conf_id))
            self.assertTrue(
                response.status_code == 200,
                msg="Open conference upgrade page")

            response = c.post(url_for('conference.payment', conference_id=self.conf_id),
                                        data={
                                            'card_number': '4000000000000002',
                                            'holder_name': 'Jiannan Wang',
                                            'exp': '04/20',
                                            'security_code': '1234',
                                            'stripeToken': 'tok_chargeDeclined'
                                        }, follow_redirects=True)
            self.assertTrue(
                response.status_code == 200, msg="VISA Declined Case for Conference Upgrade")
            self.assertTrue('Your card was declined' in response.data, msg="Card Declined - Conference Upgrade")

            # incorrect security code case
            response = c.post(url_for('conference.payment', conference_id=self.conf_id),
                              data={
                                  'card_number': '4000000000000127',
                                  'holder_name': 'Jiannan Wang',
                                  'exp': '04/20',
                                  'security_code': '1234',
                                  'stripeToken': 'tok_chargeDeclinedIncorrectCvc'
                              }, follow_redirects=True)
            self.assertTrue(
                response.status_code == 200, msg="VISA Incorrect Security Code Case for Conference Upgrade")
            self.assertTrue('Your card&#39;s security code is incorrect' in response.data, msg="Incorrect Security Code - Conference Upgrade")

            # successful case
            response = c.post(url_for('conference.payment', conference_id=self.conf_id),
                              data={
                                  'card_number': '4242424242424242',
                                  'holder_name': 'Jiannan Wang',
                                  'exp': '04/20',
                                  'security_code': '1234',
                                  'stripeToken': 'tok_visa'
                              }, follow_redirects=True)
            self.assertTrue(
                response.status_code == 200, msg="VISA Success Case for Conference Upgrade")
            self.assertTrue('Thank you for supporting our product.' in response.data,
                            msg="Success - Conference Upgrade")

    def test_conference_upgrade_resend_receipt(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'admin@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login as admin failed.")

            response = c.post(url_for('api.resend_conference_transaction_email'),
                              headers=self.get_api_headers('admin@conferency.com', 'test'),
                              data=json.dumps({
                                      'transaction_id': 1
                                  }))
            self.assertTrue(response.status_code == 200, msg='Resend receipt')

    def test_conference_upgrade_refund(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'admin@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login as admin failed.")

            response = c.post(url_for('api.refund_conference_transaction'),
                              headers=self.get_api_headers('admin@conferency.com', 'test'),
                              data=json.dumps({
                                      'transaction_id': 1
                                  }))
            self.assertTrue(response.status_code == 200, msg='Conference refund')
