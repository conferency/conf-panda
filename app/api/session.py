from flask import session
from . import api


@api.route('/ping', methods=['POST'])
def ping():
    session.modified = True
    return 'Success', 200
