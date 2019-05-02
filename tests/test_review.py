import json
import unittest
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import xlsxwriter
from random import sample
from flask import url_for
from app import create_app
from base64 import b64encode
from app.models import User, Paper, Conference


class ReviewTestCase(unittest.TestCase):

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

    def test2_add_review(self):
        # login with the chair account and switch to icis2015
        response = self.client.post(url_for('auth.login'), data={
            'email': 'pc@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue("Durant" in response.data, msg="Login")
        user = User.query.filter_by(
            email='pc@conferency.com').first()
        user.set_conference_id(2)

        paper_id = -1
        for _paper in user.papers_reviewed.all():
            review = user.reviews.filter_by(paper_id=_paper.id).first()
            if review is None:
                paper_id = _paper.id
                break
        response = self.client.post(
            url_for('review.edit_review', paper_id=paper_id),
            data={
                'evaluation': '5',
                'confidence': '4',
                'review_body': 'I think this is a good paper.',
                'confidential_remarks': 'I am not sure.'
            }, follow_redirects=True)
        self.assertTrue('I think this is a good paper.' in response.data)
        self.assertTrue(
            'I think this is a good paper.' in user.reviews.filter_by(
                paper_id=paper_id).first().review_body)

    def test3_update_review(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'pc@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue("Durant" in response.data, msg="Login")
        user = User.query.filter_by(
            email='pc@conferency.com').first()
        # user.set_conference_id(2)
        review = user.reviews.first()
        response = self.client.post(
            url_for('review.edit_review', paper_id=review.paper_id),
            data={
                'evaluation': '1',
                'confidence': '5',
                'review_body': 'This paper is rubbish.',
                'confidential_remarks': 'I am sure.'
            }, follow_redirects=True)
        self.assertTrue('This paper is rubbish.' in response.data)
        self.assertTrue('This paper is rubbish.' in user.reviews.filter_by(
            paper_id=review.paper_id).first().review_body)

    def test1_assign_review(self):
        pc = User.query.filter_by(email='pc@conferency.com').first()
        paper = Paper.query.filter(
            Paper.conference_id == 2, ~Paper.reviewers.contains(pc)).first()
        # api call
        response = self.client.post(
            url_for('api.add_review_assginment', paper_id=paper.id),
            headers=self.get_api_headers('chair@conferency.com', 'test'),
            data=json.dumps({'user_id': pc.id}))
        self.assertTrue(response.status_code == 201)

    def test4_import_review_assignment(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        conference = Conference.query.get(2)
        num_reviewers = 4
        response = self.client.get(
            url_for('api.download_review_assignment_excel',
                    conference_id=conference.id, reviewers=num_reviewers),
            headers=self.get_api_headers('chair@conferency.com', 'test'))
        self.assertTrue(response.status_code == 200)
        reviewers = conference.reviewers
        # generate excel file
        output = StringIO.StringIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('assignments_list')
        worksheet_pc = workbook.add_worksheet('reviewers_list')
        # Add a format for the header cells.
        header_format = workbook.add_format({
            'border': 1,
            'bg_color': '#1ab394',
            'bold': True,
            'text_wrap': False,
            'valign': 'vcenter',
            'indent': 1,
        })
        # unlocked = workbook.add_format({'locked': 0})
        # fill the pc sheet
        reviewers = conference.reviewers
        for index, reviewer in enumerate(reviewers):
            worksheet_pc.write(
                index, 0, reviewer.id)
            worksheet_pc.write(
                index, 1,
                '{} ({}) {{{}}}'.format(reviewer.full_name.encode('utf-8'),
                                        reviewer.email,
                                        reviewer.id).decode('utf-8'))
        worksheet.write(0, 0, 'ID', header_format)
        worksheet.write(0, 1, 'Title', header_format)
        worksheet.write(0, 2, 'Authors', header_format)
        for i in range(num_reviewers):
            worksheet.write(0, i + 3, 'Reviewer ' + str(i + 1), header_format)
        papers = conference.get_papers.all()
        for index in range(len(papers)):
            worksheet.write(index + 1, 0, papers[index].id)
            worksheet.write(index + 1, 1, papers[index].title)
            worksheet.write(
                index + 1, 2,
                ', '.join('{}({})'.format(
                    author.full_name.encode('utf-8'),
                    author.organization.encode('utf-8')
                ) for author in papers[index].authors_list).decode('utf-8'))
            for j, reviewer in enumerate(sample(reviewers, num_reviewers)):
                worksheet.write(
                    index + 1,
                    j + 3,
                    '{} ({}) {{{}}}'.format(reviewer.full_name.encode('utf-8'),
                                            reviewer.email,
                                            reviewer.id).decode('utf-8'))
        worksheet.data_validation(
            1, 3, len(papers), num_reviewers + 2,
            {
                'validate': 'list',
                'source': '=reviewers_list!$B$1:$B${}'.format(len(reviewers)),
                'input_title': 'Select a reviewer in the list',
            })
        # worksheet.protect()
        worksheet_pc.protect()
        workbook.close()
        output.seek(0)
        response = self.client.post(
            url_for('conference.import_review_assignment',
                    conference_id=conference.id),
            data={
                'file': (output, 'test.xlsx')
            },
            content_type='multipart/form-data',
            buffered=True)
        self.assertTrue(response.status_code == 201 or
                        response.status_code == 400)
