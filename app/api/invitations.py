# -*- coding: utf-8 -*-
"""Apis for invitations."""


from flask import request, url_for
from datetime import datetime
from flask_login import current_user
from ..models import Track, Invitation, User, Role, InvitationStatus
from . import api
from .errors import bad_request, forbidden
from .. import db
from ..utils.email_operation import send_email
from .authentication import auth


@api.route('/invitations/<token>/accept', methods=['POST'])
@auth.login_required
def accept_invitation(token):
    """Invitee to accept invitation."""
    # check if invitation is expired
    data = User.email_invitation(token)
    if not data:
        return forbidden('This invitation is invalid or has expired. \
                         If you have questions, please contact the inviter.')
    else:
        invitation_email, invitation_role, invitation_track_id = data
        # validate invitation
        if not invitation_email == current_user.email:
            # current user is not the invitee
            return forbidden('You don\'t have the permission to accept this \
                             invitation.')
        role = Role.query.filter_by(name=invitation_role).first()
        track = Track.query.filter_by(id=invitation_track_id,
                                      status=True).first()
        if not role or not track:
            return forbidden('The invitation is invalid.')
        invitation = Invitation.validate_invitation(token)
        if not invitation:
            return forbidden('The invitation cannot be accepted anymore.')
        # accept the invitation
        current_user.join_track(track, role)
        if not current_user.is_joined_conference(track.conference):
            current_user.join_conference(track.conference)
        invitation.accept_invitation(current_user)
        return 'You accepted the invitation.', 200


@api.route('/invitations/<token>/decline', methods=['POST'])
@auth.login_required
def decline_invitation(token):
    """Invitee to accept invitation."""
    # check if invitation is expired
    data = User.email_invitation(token)
    if not data:
        return forbidden('This invitation is invalid or has expired. \
                         If you have questions, please contact the inviter.')
    else:
        invitation_email, invitation_role, invitation_track_id = data
        # validate invitation
        if not invitation_email == current_user.email:
            # current user is not the invitee
            return forbidden('You don\'t have the permission to decline this \
                             invitation.')
        invitation = Invitation.validate_invitation(token)
        if not invitation:
            return forbidden('The invitation cannot be declined anymore.')
        # decline the invitation
        invitation.decline_invitation()
        return 'You declined the invitation.', 200


@api.route('/invitations/<int:invitation_id>/<operation>', methods=['PUT'])
@auth.login_required
def invitation_operation_email(invitation_id, operation):
    invitation = Invitation.query.filter_by(
        id=request.json.get('invitation_id'),
        invitee_status='Pending').first()
    if invitation:
        if not current_user.is_chair(invitation.conference):
            return forbidden('Not allowed')
        if operation == 'resend':
            invitation.invitation_time = datetime.now()
            invitation.token = current_user.generate_email_invitation_token(
                invitation.invitee_email,
                invitation.invitee_role,
                invitation.track_id)
            db.session.add(invitation)
            db.session.commit()
            if send_email(invitation.invitee_email,
                          invitation.email_content['subject'],
                          'email/custom_invitation',
                          reply_to=invitation.conference.contact_email,
                          content=invitation.email_content['content'],
                          join_link=url_for(
                              'auth.invitation_register',
                              token=invitation.token, _external=True),
                          decline_link=url_for(
                              'auth.invitation_decline',
                              token=invitation.token, _external=True),
                          conference=invitation.conference, test_email=False):
                return 'Success', 200
        elif operation == 'revoke':
            if invitation.invitee_status != InvitationStatus.PENDING:
                return bad_request('Invalid invitation')
            invitation.invitee_status = InvitationStatus.REVOKED
            db.session.add(invitation)
            db.session.commit()
            return 'Success', 200
    else:
        return bad_request('Invalid invitation')
