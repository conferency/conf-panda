import unittest
from flask import url_for
from app import create_app


# this test case tests every page on the main manu
# simple check of 200 and 302


class StripeTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_visa_success_case(self):
        # 4242424242424242 visa successful

        # Fetch registration page
        response = self.client.get(url_for('main.conf_registration', conf_name="icis2015"))
        self.assertTrue(
            response.status_code == 200, msg="Registration Page ICIS2015")

        response = self.client.post(url_for('conference.attendee_registration', conference_id="2"),
                                    data={
                                        'tickets': '1',
                                        'attendee_first_name': 'Harry',
                                        'attendee_last_name': 'Wang',
                                        'attendee_email': 'test@conferency.com',
                                        'attendee_affiliation': 'University of Delaware',
                                        '0_0': 'Justin Zobel',
                                        '1_1': 'I\'m a professor.',
                                        '2_1': 'Yes',
                                        '3_1': 'China',
                                        'card_number': '4242424242424242',
                                        'holder_name': 'Jiannan Wang',
                                        'month': '4',
                                        'year': '2025',
                                        'security_code': '1234',
                                        'street': '42 Amstel Ave',
                                        'city': 'Newark',
                                        'state': 'Delaware',
                                        'country': 'United States',
                                        'zipcode': '19716',
                                        'stripeToken': 'tok_visa'
                                    }, follow_redirects=True)
        self.assertTrue(
            response.status_code == 200, msg="VISA Success Case for ICIS2015 Registration")
        self.assertTrue('Registration Complete' in response.data, msg="Registration Page ICIS2015")

    def test_declined_case(self):
        # 4000000000000002	Charge will be declined with a card_declined code.

        response = self.client.post(url_for('conference.attendee_registration', conference_id="2"),
                                    data={
                                        'tickets': '1',
                                        'attendee_first_name': 'Harry',
                                        'attendee_last_name': 'Wang',
                                        'attendee_email': 'test@conferency.com',
                                        'attendee_affiliation': 'University of Delaware',
                                        '0_0': 'Justin Zobel',
                                        '1_1': 'I\'m a professor.',
                                        '2_1': 'Yes',
                                        '3_1': 'China',
                                        'card_number': '4000000000000002',
                                        'holder_name': 'Jiannan Wang',
                                        'month': '4',
                                        'year': '2025',
                                        'security_code': '1234',
                                        'street': '42 Amstel Ave',
                                        'city': 'Newark',
                                        'state': 'Delaware',
                                        'country': 'United States',
                                        'zipcode': '19716',
                                        'stripeToken': 'tok_chargeDeclined'
                                    }, follow_redirects=True)
        self.assertTrue(
            response.status_code == 200, msg="VISA Declined Case for ICIS2015 Registration")
        self.assertTrue('Your card was declined' in response.data, msg="Registration Page ICIS2015")

    def test_incorrect_security_code_case(self):
        # 4000000000000127	Charge will be declined with an incorrect_cvc code

        response = self.client.post(url_for('conference.attendee_registration', conference_id="2"),
                                    data={
                                        'tickets': '1',
                                        'attendee_first_name': 'Harry',
                                        'attendee_last_name': 'Wang',
                                        'attendee_email': 'test@conferency.com',
                                        'attendee_affiliation': 'University of Delaware',
                                        '0_0': 'Justin Zobel',
                                        '1_1': 'I\'m a professor.',
                                        '2_1': 'Yes',
                                        '3_1': 'China',
                                        'card_number': '4000000000000127',
                                        'holder_name': 'Jiannan Wang',
                                        'month': '4',
                                        'year': '2025',
                                        'security_code': '1234',
                                        'street': '42 Amstel Ave',
                                        'city': 'Newark',
                                        'state': 'Delaware',
                                        'country': 'United States',
                                        'zipcode': '19716',
                                        'stripeToken': 'tok_chargeDeclinedIncorrectCvc'
                                    }, follow_redirects=True)
        self.assertTrue(
            response.status_code == 200, msg="VISA Incorrect Security Code Case for ICIS2015 Registration")
        self.assertTrue('Your card&#39;s security code is incorrect' in response.data, msg="Registration Page ICIS2015")
