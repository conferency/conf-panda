import unittest
from flask import url_for
from app import create_app
from app.models import Paper, PaperStatus, User, paper_reviewer, \
    paper_author, Conference, JoinTrack, Review
from sqlalchemy import and_
from app import db


class PaperSubmissionTestCase(unittest.TestCase):


    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

        conference = Conference.query.get(2)
        self.author_notification = {
            'status_select': PaperStatus.ACCEPTED,
            'paper_ids': [paper.id for paper in Paper.query.filter(
                Paper.conference_id == conference.id,
                Paper.status == PaperStatus.ACCEPTED).all()],
            'email_subject': 'Congrats',
            'email_content': '''
            <p>Dear *FIRST_NAME*,</p>
            <p><br></p>
            <p>We are pleased to inform you that your paper titled
            "*TITLE*" has been accepted for presentation at *CONFERENCE_NAME* and will be
            published in the workshop proceedings. Your paper
            acceptance is subject to: (a) receipt of your electronic
            submission of the final manuscript, and (b) at least one
            author of your paper registering and participating in *CONFERENCE_SHORTNAME*.
            The deadline for your final electronic
            submission is ###. </p><p>Please revise your manuscript based
            on the reviewers comments, which are attached at the end of
            this message. The paper preparation must follow the template
            found at xxx We thank you again for your contribution to
            *CONFERENCE_SHORTNAME* and look forward to seeing you in ###.</p>
            <p><br></p>
            <p>Best Regards,</p>
            <p>{{ current_user.full_name }}<br></p>
            <p><br></p>
            <p>*PAPER_REVIEW*</p>
            '''
        }

        papers = conference.get_papers.outerjoin(
            paper_reviewer,
            Paper.id == paper_reviewer.c.paper_id).outerjoin(
            Review, and_(Review.reviewer_id == paper_reviewer.c.user_id,
                         Paper.id == Review.paper_id)
                         ).filter(Review.id == None).all()
        user_ids = [
            user.id for paper in papers for user in
            paper.reviewers if not paper.if_has_review(user)]

        self.pc_notification = {
            'receiver_type': 'checkbox_missing',
            'email_receivers': user_ids,
            'email_subject': 'Congrats',
            'email_content': '''
            <p>Dear *FIRST_NAME*,</p>
            <p><br></p>
            <p>I recently sent your some review assignments but you have not finished them yet.
                Please find below the list of papers assigned to you for reviewing.</p>
            <p>You can login at *PAPER_REVIEW_SYSTEM* to start the process.</p>
            <p><br></p>
            <p>Best regards,</p>
            <p>{{ current_user.full_name }}</p>
            <p><br></p>
            <p>*MISSING_REVIEWED_PAPERS*<br></p>
            '''
        }

        self.member_notification = {
            'email_receivers': [
                member.id for member in conference.members[:5]],
            'email_subject': 'Congrats',
            'email_content': '''
            <p>Dear *FIRST_NAME*,</p>
            <p><br></p>
            <p>Please find below the list of papers assigned to you for reviewing.</p>
            <p>You can login at *PAPER_REVIEW_SYSTEM* to start the process.</p>
            <p><br></p>
            <p>Best regards,</p>
            <p>{{ current_user.full_name }}</p>
            <p><br></p>
            '''
        }

        sessions = conference.conference_schedule.get_sessions.all()
        receivers = []
        for session in sessions:
            receivers += [speaker for speaker in session.speakers.all()]
            receivers += [moderator for moderator in session.moderators.all()]
        # receivers = list(set(speakers)) + list(set(moderators))

        self.session_notification = {
            'email_receivers': [
                receiver.id for receiver in receivers],
            'email_subject': 'Congrats',
            'receiver_type': 'checkbox_all',
            'email_content': '''
            <p>Dear *FIRST_NAME*,</p>
            <p><br></p>
            <p>Please find below the list of papers assigned to you for reviewing.</p>
            <p>You can login at *SESSION_INFO* to start the process.</p>
            <p><br></p>
            <p>Best regards,</p>
            <p>{{ current_user.full_name }}</p>
            <p><br></p>
            '''
        }

    def tearDown(self):
        self.app_context.pop()

    def test1_send_to_authors(self):
        # login first
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        response = self.client.post(
            url_for('conference.send_notification',
                    conference_id=2,
                    operation='author'),
            data=self.author_notification,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Successfully Send emails' in data)

    def test2_send_to_pcs(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        response = self.client.post(
            url_for('conference.send_notification',
                    conference_id=2,
                    operation='pc'),
            data=self.pc_notification,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Successfully Send emails' in data)

    def test3_send_to_members(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        response = self.client.post(
            url_for('conference.send_notification',
                    conference_id=2,
                    operation='member'),
            data=self.member_notification,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Successfully Send emails' in data)

    def test4_send_to_sessions(self):
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)
        self.assertTrue(response.status_code == 200)
        response = self.client.post(
            url_for('conference.send_notification',
                    conference_id=2,
                    operation='session'),
            data=self.session_notification,
            follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertTrue('Successfully Send emails' in data)
