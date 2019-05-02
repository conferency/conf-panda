# -*- coding: utf-8 -*-
"""Test customized questions api."""
import unittest
from flask import url_for
from base64 import b64encode
from app import create_app
import json

json_empty = []
json_empty_option = [
    {
        'desc': 'Single Choice Single Choice Single Choice',
        'include': True,
        'numid': 0,
        'ques_type': '0',
        'require': None,
        'uuid': '0',
        'options': []
    }
]
json_one_option = [
    {
        'desc': 'Single Choice Single Choice Single Choice',
        'include': True,
        'numid': 0,
        'ques_type': '0',
        'require': None,
        'uuid': '0',
        'options': ['一']
    }
]
json_question = [
    {
        'desc': 'Essay Textbox Essay Textbox Essay Textbox Essay Textbox Essay \
        Textbox',
        'include': True,
        'numid': 3,
        'ques_type': '3',
        'require': None,
        'uuid': '0'
    },
    {
        'desc': 'Single-Line Textbox Single-Line Textbox Single-Line Textbox',
        'include': True,
        'numid': 2,
        'ques_type': '2',
        'require': None,
        'uuid': '0'
    },
    {
        'desc': 'Single Choice Single Choice Single Choice',
        'include': True,
        'numid': 0,
        'ques_type': '0',
        'require': None,
        'uuid': '0',
        'options': ['一', '二', '三']
    },
    {
        'desc': '多项选择',
        'include': True,
        'numid': 1,
        'ques_type': '1',
        'require': None,
        'uuid': '0',
        'options': [
            "option1, option1, option1",
            "option2, option2, option2",
            "option3, option3, option3"]
    }
]

class CustomeizedTQuestionsAPITestCase(unittest.TestCase):
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
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 401)
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 401)
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 401)

    def test_no_permission(self):
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 403)
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 403)
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            headers=self.get_api_headers('author@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 403)

    def test_empty_question(self):
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty))
        self.assertTrue('Empty question list' == json.loads(
                        response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty))
        self.assertTrue('Empty question list' == json.loads(
                   response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty))
        self.assertTrue('Empty question list' == json.loads(
                   response.data.decode('utf-8')).get('message'))

    def test_empty_option(self):
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty_option))
        self.assertTrue('Missing options' == json.loads(
                   response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty_option))
        self.assertTrue('Missing options' == json.loads(
                   response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_empty_option))
        self.assertTrue('Missing options' == json.loads(
                   response.data.decode('utf-8')).get('message'))

    def test_one_option(self):
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_one_option))
        self.assertTrue('Options less than two' == json.loads(
                   response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_one_option))
        self.assertTrue('Options less than two' == json.loads(
                   response.data.decode('utf-8')).get('message'))
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_one_option))
        self.assertTrue('Options less than two' == json.loads(
                   response.data.decode('utf-8')).get('message'))

    def test_put_questions(self):
        response = self.client.put(
            url_for('api.update_submission_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 200)
        response = self.client.put(
            url_for('api.update_review_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 200)
        response = self.client.put(
            url_for('api.update_registration_question', conference_id=2),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps(json_question))
        self.assertTrue(response.status_code == 200)

    def test_del_questions(self):
        pass
