import unittest
from flask import url_for
from app import create_app
from flask.ext.login import current_user
from cStringIO import StringIO
from app.models import Paper, User, UserDoc
from app import db

class PaperEditTestCase(unittest.TestCase):
    paper_1 = {
        'track_id': '3',
        'title': 'A paper that will be edited',
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

    paper_edit = {
        'track_id': '4',
        'title': 'A paper that has been edited',
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
        'author_firstname_3': 'David W. K',
        'author_lastname_3': 'Bitch',
        'author_email_3': 'uvw@conferency.com',
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

    def test1_submit_paper(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")

            current_user.set_conference_id(2)

            response = c.get(
                url_for('conference.conference_submission_add',
                        conference_id=2))
            self.assertTrue(
                response.status_code == 200, msg="Add Submission ICIS2015")

            response = c.post(url_for('paper.uploadfile'),
                              data={
                                  'paper': (StringIO('my file contents'),
                                            'hello world.pdf')
                              })
            self.assertTrue(
                response.status_code == 201, msg="Upload file")

            response = c.post(
                url_for('conference.conference_submission_add',
                        conference_id=2),
                data=self.paper_1, follow_redirects=True)

            self.assertTrue(
                Paper.query.order_by(Paper.id.desc()).first().title ==
                self.paper_1['title'],
                msg="Upload paper")

    def test2_edit_paper(self):
        edit_user = User.query.filter_by(email='peter@conferency.com').first()
        edit_user.password = 'test'
        db.session.add(edit_user)
        db.session.commit()
        response = self.client.post(url_for('auth.login'), data={
            'email': 'peter@conferency.com',
            'password': 'test'
        }, follow_redirects=True)

        self.assertTrue(
            response.status_code == 200, msg="Login failed.")
        paper = Paper.query.filter_by(title=self.paper_1['title']).first()
        response = self.client.get(url_for('paper.edit_paper_info',
                                           paper_id=paper.id))
        self.assertTrue(response.status_code == 200)
        response = self.client.post(url_for('paper.uploadfile'),
                                    data={
                                        'paper': (StringIO('my file contents'),
                                                  'hello world.pdf')
                                    })
        self.assertTrue(
            response.status_code == 201, msg='Upload file')
        file_id = UserDoc.query.filter(
            UserDoc.uploader_id == edit_user.id).first().id
        if paper:
            self.paper_edit['filename'] = str(file_id) + ','
            response = self.client.post(url_for('paper.edit_paper_info',
                                                paper_id=paper.id),
                                        data=self.paper_edit,
                                        follow_redirects=True)
            self.assertTrue(
                Paper.query.filter_by(
                    title='A paper that has been edited').first().id == paper.id,
                msg='Cannot find the paper.')
        else:
            self.assertTrue(False, msg='Cannot find the paper.')
