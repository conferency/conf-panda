# -*- coding: utf-8 -*-
"""Test promo codes api."""
import unittest
import json
from flask import url_for
from base64 import b64encode
from app import create_app
from app.models import PromoCode


promo_code_1 = {
    'promo_code': 'TAKE10OFF',
    'promo_type': 'fixed_amount',
    'promo_value': '10',
    'promo_currency': 'USD',
    'promo_limit': '-1',
    'promo_start': '2019-12-1',
    'promo_end': '2019-12-30'
}

promo_code_2 = {
    'promo_code': 'TAKE10%OFF',
    'promo_type': 'percentage',
    'promo_value': '10',
    'promo_limit': '50',
    'promo_currency': 'USD',
    'promo_start': '2019-12-1',
    'promo_end': '2019-12-30'
}

promo_code_3 = {
    'promo_code': 'TAKE10OFF',
    'promo_type': 'fixed_amount',
    'promo_value': '10',
    'promo_limit': '-1',
    'promo_currency': 'CNY',
    'promo_start': '2019-12-1',
    'promo_end': '2019-12-30'
}

promo_code_4 = {
    'promo_code': 'FREESESSION',
    'promo_type': 'fixed_amount',
    'promo_value': '200',
    'promo_limit': '',
    'promo_currency': 'CNY',
    'promo_start': '2019-12-1',
    'promo_end': '2019-12-30'
}

update_promo_code_1 = {
    'promo_code_id': '1',
    'action': 'disable'
}

update_promo_code_2 = {
    'promo_code_id': '1',
    'action': 'enable'
}

update_promo_code_3 = {
    'promo_code_id': '1',
    'action': 'edit',
    'promo_code': {
        'promo_code': 'TAKE20OFF',
        'promo_type': 'fixed_amount',
        'promo_value': '20',
        'promo_limit': '-1',
        'promo_currency': 'USD',
        'promo_start': '2019-12-1',
        'promo_end': '2019-12-30'
    }
}

class romoCodeAPITestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def get_api_headers(self, username, password):
        return {
            'Authorization': 'Basic ' + b64encode(
                (username + ':' + password).encode('utf-8')).decode('utf-8'),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

    def test_no_auth(self):
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            data=json.dumps(promo_code_1))
        self.assertTrue(response.status_code == 401)
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            data=json.dumps(promo_code_1))
        self.assertTrue(response.status_code == 401)
        response = self.client.put(
            url_for('api.update_promo_code', registration_id=2),
            data=json.dumps(update_promo_code_1))
        self.assertTrue(response.status_code == 401)

    def test_no_permission(self):
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('pc@conferency.com', 'test'),
            data=json.dumps(promo_code_1))
        self.assertTrue(response.status_code == 403)
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps(promo_code_1))
        self.assertTrue(response.status_code == 403)
        response = self.client.put(
            url_for('api.update_promo_code', registration_id=2),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps(update_promo_code_1))
        self.assertTrue(response.status_code == 403)

    def test1_add_promo_codes(self):
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(promo_code_1))
        self.assertTrue(response.status_code == 201)
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(promo_code_2))
        self.assertTrue(response.status_code == 201)

    def test2_add_invalid_promo_codes(self):
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(promo_code_3))
        self.assertTrue(response.status_code == 400)
        response = self.client.post(
            url_for('api.add_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(promo_code_4))
        self.assertTrue(response.status_code == 400)

    def test3_update_promo_codes(self):
        # test disable, enable
        response = self.client.put(
            url_for('api.update_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(update_promo_code_1))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('api.get_promo_code',
                    registration_id=2,
                    promo_code_id=update_promo_code_1['promo_code_id']))
        promo_code = PromoCode.query.get(update_promo_code_1['promo_code_id'])
        self.assertTrue(promo_code.status == 'Inactive')
        response = self.client.put(
            url_for('api.update_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(update_promo_code_2))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('api.get_promo_code',
                    registration_id=2,
                    promo_code_id=update_promo_code_2['promo_code_id']))
        self.assertTrue(response.status_code == 200)
        # edit promo code
        response = self.client.put(
            url_for('api.update_promo_code', registration_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(update_promo_code_3))
        self.assertTrue(response.status_code == 200)
        response = self.client.get(
            url_for('api.get_promo_code',
                    registration_id=2,
                    promo_code_id=update_promo_code_3['promo_code_id']))
        self.assertTrue('TAKE20OFF' in response.data)
