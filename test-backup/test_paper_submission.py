import unittest
from flask import url_for
from app import create_app
from flask.ext.login import current_user
from cStringIO import StringIO
from app.models import Paper


class PaperSubmissionTestCase(unittest.TestCase):
    paper_1 = {
        'track_id': '3',
        'title': 'Leafsnap: A Computer Vision System for Automatic Plant \
            Species Identification',
        'abstract': 'We describe the first mobile app for identifying plant \
            species using automatic visual recognition.',
        'keywords': 'computer,vision,system',
        'author_firstname_1': 'Neeraj',
        'author_lastname_1': 'Kumar',
        'author_email_1': 'neeraj@conferency.com',
        'author_organization_1': 'University of Washington',
        'author_country_1': 'United States',
        'author_website_1': '',
        'author_firstname_2': 'Peter N.',
        'author_lastname_2': 'Belhumeur',
        'author_email_2': 'peter@conferency.com',
        'author_organization_2': 'Columbia University',
        'author_country_2': 'United States',
        'author_website_2': '',
        'author_firstname_3': 'David W.',
        'author_lastname_3': 'Kress',
        'author_email_3': 'john@conferency.com',
        'author_organization_3': 'National Museum of Natural History, \
            Smithsonian Institution',
        'author_country_3': 'United States',
        'author_website_3': '',
        'filename': '101,'
    }

    paper_2 = {
        'track_id': '9',
        'title': 'Leafsnap: A Computer Vision System for Automatic Plant \
            Species Identification',
        'abstract': 'We describe the first mobile app for identifying plant \
            species using automatic visual recognition.',
        'keywords': 'computer,vision,system',
        'author_firstname_1': 'Neeraj',
        'author_lastname_1': 'Kumar',
        'author_email_1': 'neeraj@conferency.com',
        'author_organization_1': 'University of Washington',
        'author_country_1': 'United States',
        'author_website_1': '',
        'author_firstname_2': 'Peter N.',
        'author_lastname_2': 'Belhumeur',
        'author_email_2': 'peter@conferency.com',
        'author_organization_2': 'Columbia University',
        'author_country_2': 'United States',
        'author_website_2': '',
        'author_firstname_3': 'David W.',
        'author_lastname_3': 'Kress',
        'author_email_3': 'john@conferency.com',
        'author_organization_3': 'National Museum of Natural History, \
            Smithsonian Institution',
        'author_country_3': 'United States',
        'author_website_3': '',
        'filename': '102,'
    }

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_submission_papers(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            current_user.set_conference_id(2)

            response = c.get(url_for('submission.add_submission'))
            self.assertTrue(
                response.status_code == 200, msg="Add Submission ICIS2015")

            response = c.post(url_for('paper.uploadfile'),
                              data={
                                  'paper': (StringIO('my file contents'),
                                            'hello world.pdf')
                              })
            self.assertTrue(
                response.status_code == 201, msg="Upload file")

            response = c.post(url_for('submission.add_submission'),
                              data=self.paper_1,
                              follow_redirects=True)

            self.assertTrue(
                Paper.query.order_by(
                    Paper.id.desc()).first().title == self.paper_1['title'],
                msg="Upload paper 1")

            current_user.set_conference_id(4)

            response = c.get(url_for('submission.add_submission'))
            self.assertTrue(
                response.status_code == 200, msg="Add Submission PACIS2016")

            response = c.post(url_for('paper.uploadfile'),
                              data={
                                  'paper': (StringIO('my file contents'),
                                            'hello world.pdf')
                              })
            self.assertTrue(
                response.status_code == 201, msg="Upload file")

            response = c.post(url_for('submission.add_submission'),
                              data=self.paper_2,
                              follow_redirects=True)

            self.assertTrue(
                Paper.query.order_by(
                    Paper.id.desc()).first().title == self.paper_2['title'],
                msg="Upload paper 2")
