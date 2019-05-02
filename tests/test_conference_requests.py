# -*- coding: utf-8 -*-
import unittest
import json
from flask import url_for
from base64 import b64encode
from app import create_app
from app.models import Conference


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

    def test1_conference_request_free(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            response = c.get(url_for('conference.request_conference'))
            self.assertTrue(
                response.status_code == 200,
                msg="Open conference request page")

            response = c.get(
                url_for('conference.request_new_conference', type='new'))
            self.assertTrue(
                response.status_code == 200,
                msg='Open conference type selection page')

            response = c.get(
                url_for('conference.request_new_conference', type='free'))
            self.assertTrue(
                response.status_code == 200,
                msg='Open free conference selection page')

            response = c.post(
                url_for('conference.request_new_conference', type='free'),
                follow_redirects=True,
                data={
                                  'website_url': 'lunar.com',
                                  'short_name': 'lunar2018',
                                  'conference_name': 'My Conference',
                                  'contact_email': 'chair@conferency.com',
                                  'contact_phone': '+1234567890',
                                  'address': '1 Lunar Way',
                                  'city': 'Lunatic City',
                                  'state': 'Moon State',
                                  'country': 'Luna',
                                  'start': '2018-01-25',
                                  'end': '2018-01-26',
                                  'timezone': 'UTC',
                                  'info': 'This is my conference info',
                                  'subjects':
                                  'Accounting, Auditing & Taxation',
                                  'tags': 'this, that; another',
                                  'requester_website': 'sinisfn.com',
                                  'your_role': 'Chair',
                                  'contact_name': 'Kerry Peter',
                                  'affiliation': 'MMA',
                                  'requester_contact_phone': '+1234567890',
                                  'source_from': 'Search Engine',
                                  'referred_by': 'refer'
                              })
            self.assertTrue(
                response.status_code == 200,
                msg='Submit free conference request')

            self.assertIsNotNone(
                Conference.query.filter_by(short_name="lunar2018").first(),
                msg="Submit free conference request")

    def test2_conference_request_pro(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            response = c.get(url_for('conference.request_conference'))
            self.assertTrue(
                response.status_code == 200,
                msg="Open conference request page")

            response = c.get(
                url_for('conference.request_new_conference', type='new'))
            self.assertTrue(
                response.status_code == 200,
                msg='Open conference type selection page')

            response = c.get(
                url_for('conference.request_new_conference', type='pro'))
            self.assertTrue(
                response.status_code == 200,
                msg='Open pro conference selection page')

            response = c.post(
                url_for('conference.request_new_conference', type='pro'),
                follow_redirects=True,
                data={
                                  'website_url': 'lunar.com',
                                  'short_name': 'lunarpro2018',
                                  'conference_name': 'My Conference Pro',
                                  'contact_email': 'chair@conferency.com',
                                  'contact_phone': '+1234567890',
                                  'address': '1 Lunar Way',
                                  'city': 'Lunatic City',
                                  'state': 'Moon State',
                                  'country': 'Luna',
                                  'start': '2018-01-25',
                                  'end': '2018-01-26',
                                  'timezone': 'UTC',
                                  'info': 'This is my pro conference info',
                                  'subjects':
                                  'Accounting, Auditing & Taxation',
                                  'tags': 'this, that; another',
                                  'card_number': '4242424242424242',
                                  'holder_name': 'Jiannan Wang',
                                  'month': '4',
                                  'year': '2025',
                                  'security_code': '1234',
                                  'street': '42 Amstel Ave',
                                  'zipcode': '19716',
                                  'stripeToken': 'tok_visa',
                                  'requester_website': 'sinisfn.com',
                                  'your_role': 'PC',
                                  'contact_name': 'Kerry Peter',
                                  'affiliation': 'MMA',
                                  'requester_contact_phone': '+1234567890',
                                  'source_from': 'Search Engine',
                                  'referred_by': 'refer'
                              })
            self.assertTrue(
                response.status_code == 200,
                msg='Submit pro conference request')

            self.assertIsNotNone(
                Conference.query.filter_by(short_name="lunarpro2018").first(),
                msg="Submit pro conference request")

    def test3_no_auth(self):
        conf_id = Conference.query.filter_by(short_name="lunar2018").first().id
        response = self.client.post(
            url_for('api.edit_conference_status'),
            data=json.dumps({
                'conf_id': conf_id,
                'new_status': 'Denied',
                'is_new_conf': True
            }))
        self.assertTrue(response.status_code == 401)

    def test4_no_permission(self):
        conf_id = Conference.query.filter_by(short_name="lunar2018").first().id
        response = self.client.post(
            url_for('api.edit_conference_status'),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps({
                'conf_id': conf_id,
                'new_status': 'Denied',
                'is_new_conf': True
            }))
        self.assertTrue(response.status_code == 403)

    def test5_conference_request_update(self):
        approve_conf_id = Conference.query.filter_by(
            short_name='lunar2018').first().id
        response = self.client.post(
            url_for('api.edit_conference_status'),
            headers=self.get_api_headers('admin@conferency.com', 'test'),
            data=json.dumps({
                'conf_id': approve_conf_id,
                'new_status': 'Approved',
                'is_new_conf': True
            }))
        self.assertTrue(response.status_code == 200)

        deny_conf_id = Conference.query.filter_by(
            short_name='lunarpro2018').first().id
        response = self.client.post(
            url_for('api.edit_conference_status'),
            headers=self.get_api_headers('admin@conferency.com', 'test'),
            data=json.dumps({
                'conf_id': deny_conf_id,
                'new_status': 'Denied',
                'is_new_conf': False,
                'denial_msg': 'Cannot verify your request'
            }))
        self.assertTrue(response.status_code == 200)
