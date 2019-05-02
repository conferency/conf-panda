import unittest
from flask import url_for
from app import create_app
from flask.ext.login import current_user
from app.models import User


class MergeAccountTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test1_merge_account(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)
            self.assertTrue(
                response.status_code == 200, msg="Login failed.")
            current_user.set_conference_id(2)

            response = c.get(url_for('auth.settings'))
            self.assertTrue(
                response.status_code == 200, msg='settting page')

            response = c.post(url_for('auth.settings'),
                              data={
                                'merge_form-email': 'author@conferency.com',
                                'merge_form-password': 'test',
                                'merge_form-submit':
                                'Merge this account into your current account'
                              },
                              follow_redirects=True)
            self.assertTrue(
                'author@conferency.com has been merged into you account' in response.get_data(as_text=True))

    def test2_switch_account(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)
            self.assertTrue(
                response.status_code == 200, msg="Login failed.")
            current_user.set_conference_id(2)
            user = User.query.filter_by(email='author@conferency.com').first()
            response = c.get(url_for('auth.switch_user',
                                     user_id=user.id),
                             follow_redirects=True)
            self.assertTrue(
                'Switched to ' + user.email in response.get_data(as_text=True))
