from flask import request
from . import api
from ..utils.email_operation import send_email


@api.route('/send_email_to_support', methods=['POST'])
def support_email():
    send_email('support@conferency.com', request.json.get('subject'), 'email/support_email',
               name=request.json.get('name'), email=request.json.get('email'), message=request.json.get('message'))

    return 'Success', 200
