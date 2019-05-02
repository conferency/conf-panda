import re
import unittest
from flask import url_for
from app import create_app, db
from app.models import User

# this test case tests basic registration, login, logout


class RegisterLoginTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test1_register_login(self):
        # register a new account
        response = self.client.post(url_for('auth.register'), data={
            'email': 'johndoe@conferency.com',
            'firstname': 'John',
            'lastname': 'Doe',
            'password': 'testtest',
            'password2': 'testtest',
            'organization': 'University of Delaware',
            'location': 'Newark',
            'state': 'Delaware',
            'country': 'United States'
        })
        self.assertTrue(response.status_code == 302)

        # login with the unconfirmed new account
        response = self.client.post(url_for('auth.login'), data={
            'email': 'johndoe@conferency.com',
            'password': 'testtest'
        }, follow_redirects=True)
        # self.assertTrue(re.search(b'Hello,\s+john!', response.data))
        self.assertTrue(
            b'You have not confirmed your account yet' in response.data)

        # send a confirmation token
        user = User.query.filter_by(email='johndoe@conferency.com').first()
        token = user.generate_confirmation_token()
        response = self.client.get(url_for('auth.confirm', token=token))
        self.assertTrue(response.status_code == 302)

        # login with the confirmed new account
        response = self.client.post(url_for('auth.login'), data={
            'email': 'johndoe@conferency.com',
            'password': 'testtest'
        }, follow_redirects=True)
        # self.assertTrue(re.search(b'Hello,\s+john!', response.data))
        self.assertTrue(
            b'Dashboard' in response.data)

        # log out
        response = self.client.get(url_for('auth.logout'))
        self.assertTrue(response.status_code == 302)

    def test2_reset_password(self):
        # unregistered email
        response = self.client.post(
            url_for('auth.password_reset_request'),
            data={
                'email': 'xxxxxxx@conferency.com'
            },
            follow_redirects=True)
        self.assertTrue(
            'This email has not been registered yet' in response.get_data(
                as_text=True))
        response = self.client.post(
            url_for('auth.password_reset_request'),
            data={
                'email': 'johndoe@conferency.com'
            },
            follow_redirects=True)
        self.assertTrue(
            'An email with instructions to' in response.get_data(
                as_text=True))
        # get token
        user = User.query.filter_by(email='johndoe@conferency.com').first()
        token = user.generate_reset_token()
        response = self.client.post(
            url_for('auth.password_reset', token=token),
            data={
                'password': '11111111',
                'password2': '11111111'
            },
            follow_redirects=True)
        self.assertTrue(
            'Your password has been updated.' in response.get_data(
                as_text=True))
