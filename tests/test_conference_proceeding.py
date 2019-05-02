# -*- coding: utf-8 -*-
import unittest
import json
from flask import url_for
from base64 import b64encode
from app import create_app
from app.models import User, Conference


class ConferenceRequestsTestCase(unittest.TestCase):

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def get_api_headers(self, username, password):
        return {
            'Authorization': 'Basic ' + b64encode(
                (username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test1_conference_proceeding(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(
            response.status_code == 200, msg="Login failed.")
        current_user = User.query.filter_by(
            email='chair@conferency.com').first()
        current_user.set_conference_id(2)
        response = self.client.get(
            url_for('conference.proceedings', conference_id=2))
        self.assertTrue(
            response.status_code == 200, msg="Cannot load proceeding page")

    def test2_open_close_conference_proceeding(self):
        response = self.client.put(
            url_for('api.update_conference_config', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps({
                'setting': {
                    'show_proceeding': False
                }
            }))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('main.conf_proceedings', conf_name='icis2015'))
        self.assertTrue(
            'ICIS2015 Proceedings are not open to public.' in response.get_data(),
            msg="Close proceeding failed")

        response = self.client.put(
            url_for('api.update_conference_config', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps({
                'setting': {
                    'show_proceeding': True
                }
            }))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('main.conf_proceedings', conf_name='icis2015'))
        self.assertTrue(
            'ICIS2015 Proceedings are not open to public.' not in response.get_data(),
            msg="Open proceeding failed")

    def test3_access_code(self):
        response = self.client.put(
            url_for('api.update_conference_config', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps({
                'setting': {
                    'use_proceeding_code': True,
                    'proceeding_code': '123'
                }
            }))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('main.conf_proceedings', conf_name='icis2015'))
        self.assertTrue(
            'Enter your access code' in response.get_data(),
            msg='Access code failed')
        response = self.client.post(
            url_for('main.conf_proceedings', conf_name='icis2015'), data={
                'access_code': '456'
            }, follow_redirects=True)
        self.assertTrue(
            'Invalid Access Code' in response.get_data(),
            msg='Access code failed')
        response = self.client.post(
            url_for('main.conf_proceedings', conf_name='icis2015'), data={
                'access_code': '123'
            }, follow_redirects=True)
        self.assertTrue(
            'Invalid Access Code' not in response.get_data(),
            msg='Access code failed')

    def test4_add_papers(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        response = self.client.get(
            url_for('conference.proceedings', conference_id=2))
        self.assertTrue(
            response.status_code == 200, msg="Cannot load proceeding page")
        conference = Conference.query.get(2)
        accepted_papers = conference.papers.filter_by(status='Accepted').all()
        if accepted_papers:
            for paper in accepted_papers:
                response = self.client.put(
                    url_for('api.edit_paper', paper_id=paper.id),
                    headers=self.get_api_headers('chair@conferency.com', 'test'),
                    data=json.dumps({
                        'proceeding_included': True
                    }))
                self.assertTrue(
                    response.status_code == 200, msg='Add paper failed')
        response = self.client.post(
            url_for('main.conf_proceedings', conf_name='icis2015'), data={
                'access_code': '123'
            }, follow_redirects=True)
        self.assertTrue(
            all(paper.title in response.get_data().decode('utf-8') for paper in accepted_papers),
            msg='Show papers failed')
