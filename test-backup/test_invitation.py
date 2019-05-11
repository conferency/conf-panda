"""this test case tests conference invitation"""
import unittest
import json
import random
import string
from bs4 import BeautifulSoup
from flask import url_for
from app import create_app
from app.models import User, Conference, Track, Invitation, InvitationStatus


class InvitationTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app('testing')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        cls.client = cls.app.test_client(use_cookies=True)

    def setUp(self):
        self.revoked_invitation_id = ''
        self.sitename = 'ICIS2015'
        self.conference_invitations = {
            "emails_without_name":
                ["testa@conferency.com", "testb@conferency.com"],
            "emails_with_name": [
                "cfirstname clastname testc@conferency.com",
                "dfirstname dlastname testd@conferency.com"],
            "subject": "Conference Invitation",
            "content": "This is the invitation for the *CONFERENCE_NAME* \
            conference, you can view *CONFERENCE_WEBSITE**CONFERENCE_WEBSITE* \
            to see detail"
        }
        self.track_invitations = {
            "emails_without_name":
                ["teste@conferency.com", "testf@conferency.com"],
            "emails_with_name": [
                "gfirstname glastname testg@conferency.com",
                "hfirstname hlastname testh@conferency.com"],
            "subject": "Track Invitation",
            "content": "This is the invitation for the conference, you can \
            view *CONFERNCE_URL* to see the detail"
        }

    @classmethod
    def tearDownClass(cls):
        cls.app_context.pop()

    def switchSite(self, conf_name, user_email):
        conf_id = Conference.query.filter_by(
            short_name=conf_name.lower()).first()
        current_user = User.query.filter_by(email=user_email).first()
        if conf_id and current_user:
            current_user.set_conference_id(conf_id.id)
        else:
            raise Exception("Conference or User Not Found")

    def random_token(self):
        return ''.join(
            random.choice(string.ascii_uppercase +
                          string.ascii_lowercase +
                          string.digits) for _ in range(30))

    def doConferenceInvitation(self, email, conference_id=2):
        without_name = {
            "email_subject": email["subject"],
            "email_content": email["content"],
            "role": 'Chair',
            "emails_default": ','.join(email['emails_without_name'])
        }
        response = self.client.post(
            "/conference/" + str(conference_id) + "/conference_invitations",
            data=without_name)
        self.assertIn("Invitation emails sent.",
                      response.data, "Emails sent properly.")
        self.assertTrue(response.status_code == 200)

        with_name = {
            "email_subject": email["subject"],
            "email_content": email["content"],
            "role": 'Program Committee',
            "emails_default": '\r\n'.join(email['emails_with_name']),
            "invitee_with_name": True
        }
        response = self.client.post(
            "/conference/" + str(conference_id) + "/conference_invitations",
            data=with_name)
        # print response.data
        self.assertIn("Invitation emails sent.",
                      response.data, "Emails sent properly.")
        self.assertTrue(response.status_code == 200)

    def doTrackInvitation(self, email, conference_id=2):
        tracks = Track.query.filter_by(
            conference_id=conference_id,
            default=False, status=True).all()
        without_name = {
            "email_subject": email["subject"],
            "email_content": email["content"],
            "role": 'Track Program Committee',
            "track_id": tracks[0].id,
            "emails_default":
                ','.join(email["emails_without_name"])
        }

        response = self.client.post(
            '/conference/' + str(conference_id) + '/track_invitations',
            data=without_name)
        self.assertIn("Invitation emails sent.",
                      response.data, "Emails sent properly.")
        self.assertTrue(response.status_code == 200)

        with_name = {
            "email_subject": email["subject"],
            "email_content": email["content"],
            "role": 'Track Program Committee',
            "track_id": tracks[0].id,
            "emails_default":
                '\r\n'.join(email["emails_with_name"]),
            "invitee_with_name": True
        }

        response = self.client.post(
            '/conference/' + str(conference_id) + '/track_invitations',
            data=with_name)
        self.assertIn("Invitation emails sent.",
                      response.data, "Emails sent properly.")
        self.assertTrue(response.status_code == 200)

    def get_invitation_id(self, data, email):
        soup = BeautifulSoup(data, 'html.parser')
        td = soup.find('td', string=email)
        if td is None:
            self.assertTrue(False)
        td_id = td.parent.find('button', {'data-operation': 'revoke'})
        if td_id is None:
            self.assertTrue(False)
        return td_id['data-invitation-id']
    # def getInvitations(self, conference_id=2):
    #     response = self.client.get(
    #         "conference/" + str(conference_id) + "/invitation_pending")
    #     soup = BeautifulSoup(response.data, 'html.parser')
    #     invitation_status = {}
    #     for tr in soup.select("#tab-2 > div > div > table > tbody > tr"):
    #         tds = tr.find_all("td")
    #         email = re.search(r'\w*@conferency\.com', tds[0].string).group(0)
    #         invitation_status[email] = {
    #             "role": tds[2].string,
    #             "status": tds[6].string
    #         }
    #     return invitation_status

    def test1_prepare_login(self):
        """Login with the chair account."""
        response = self.client.post(url_for('auth.login'), data={
            'email': 'chair@conferency.com',
            'password': 'test'
        }, follow_redirects=True)

        # redirect to dashboard with Main conf selected
        self.assertTrue(
            b'Stephen' in response.data, msg="Dashboard Main")

    def test2_conference_invitation(self):
        """Conference invitation."""
        self.switchSite("ICIS2015", "chair@conferency.com")
        self.doConferenceInvitation(self.conference_invitations)
        # self.doTrackInvitation(self.email_1, "Track Chair")
        #
        # status = self.getInvitations()
        # for er in self.email_1["emails_role"]:
        #     self.assertTrue(er in status.keys())
        #     self.assertEqual(status[er]["role"], "Chair")
        #
        # for etc in self.email_1["emails_track_chair"]:
        #     self.assertTrue(etc in status.keys())
        #     print status[etc]
        #     self.assertEqual(status[etc]["role"], "Track Chair")

    def test3_track_invitation(self):
        self.doTrackInvitation(self.track_invitations)

    def test7_invalid_invitation(self):
        """Invalid invitations."""
        # wrong token
        response = self.client.get(
            url_for('auth.invitation_register',
                    token=self.random_token()),
            follow_redirects=True)
        self.assertTrue('The link is invalid or has expired.' in response.data)
        # revoked token
        revoked_invitation = Invitation.query.filter_by(
            invitee_email=self.conference_invitations['emails_without_name'][0],
            invitee_status=InvitationStatus.REVOKED).first()
        if revoked_invitation is None:
            self.assertTrue(False)
        response = self.client.get(
            url_for('auth.invitation_register',
                    token=revoked_invitation.token),
            follow_redirects=True)
        self.assertTrue('This invitation has been revoked.' in response.data)
        # joined token
        join_invitation = Invitation.query.filter_by(
            invitee_email=self.conference_invitations['emails_without_name'][1],
            invitee_status=InvitationStatus.JOINED).first()
        if join_invitation is None:
            self.assertTrue(False)
        response = self.client.get(
            url_for('auth.invitation_register',
                    token=join_invitation.token),
            follow_redirects=True)
        self.assertTrue('Invitation has been redeemed.' in response.data)
        # declined token
        decline_invitation = Invitation.query.filter_by(
            invitee_email=self.track_invitations['emails_without_name'][0],
            invitee_status=InvitationStatus.DECLINED).first()
        if decline_invitation is None:
            self.assertTrue(False)
        response = self.client.get(
            url_for('auth.invitation_register',
                    token=decline_invitation.token),
            follow_redirects=True)
        self.assertTrue('Invitation has expired.' in response.data)

    def test4_revoke_invitation(self):
        """Revoke invitation."""
        response = self.client.get(
            url_for('conference.invitation_pending', conference_id=2))
        revoked_invitation_id = self.get_invitation_id(
            response.data,
            self.conference_invitations['emails_without_name'][0])
        response = self.client.put(
            url_for('api.invitation_operation_email',
                    invitation_id=revoked_invitation_id,
                    operation='revoke'),
            headers={'Content-Type': 'application/json'},
            data=json.dumps({
                'invitation_id': revoked_invitation_id,
                'operation': 'revoke'}))
        self.assertTrue(response.status_code == 200)

    def test5_accept_invitation(self):
        join_invitation = Invitation.query.filter_by(
            invitee_email=self.conference_invitations['emails_without_name'][1],
            invitee_status=InvitationStatus.PENDING).first()
        new_user = {
            'firstname': 'new',
            'lastname': 'user',
            'email': join_invitation.invitee_email,
            'password': '11111111',
            'password2': '11111111',
            'organization': 'ABCDEF .Inc',
            'location': 'Newark',
            'state': 'DE',
            'country': 'US',
            'note': 'Thanks for the invitation.'
        }
        response = self.client.post(
            url_for('auth.invitation_register',
                    token=join_invitation.token),
            data=new_user,
            follow_redirects=True)
        self.assertTrue('Congratulations.' in response.data)

    def test6_decline_invitation(self):
        declined_invitation = Invitation.query.filter_by(
            invitee_email=self.track_invitations['emails_without_name'][0],
            invitee_status=InvitationStatus.PENDING).first()
        response = self.client.post(
            url_for('auth.invitation_decline',
                    token=declined_invitation.token),
            data={'note': 'Sorry too busy.'},
            follow_redirects=True)
        self.assertTrue('You have declined the invitation.' in response.data)
