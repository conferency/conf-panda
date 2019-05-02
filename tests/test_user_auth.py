# import unittest
# from flask import url_for
# from app import create_app
# from app.models import Paper, PaperStatus, User, paper_reviewer, \
#     paper_author, Conference, JoinTrack, Review
# from sqlalchemy import and_
# from app import db
#
# class PaperEditTestCase(unittest.TestCase):
#     def setUp(self):
#         self.app = create_app('testing')
#         self.app_context = self.app.app_context()
#         self.app_context.push()
#         self.client = self.app.test_client(use_cookies=True)
#
#     def tearDown(self):
#         self.app_context.pop()
#
#     def test1_reset_password(self):
#
