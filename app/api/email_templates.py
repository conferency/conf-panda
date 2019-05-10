from flask import jsonify, request
from flask_login import login_required, current_user
from ..models import EmailTemplate, Conference
from . import api
from .errors import not_found


@api.route('email_templates')
def get_email_templates():
    pass


@api.route('/conferences/<int:conference_id>/email_template', methods=['POST'])
def add_email_template(id):
    pass


@api.route('/conferences/<int:conference_id>/email_template')
@login_required
def get_email_template(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    email_template = conference.email_templates.filter_by(user_id=current_user.id,
                                                          name=request.args.get('template_name', '')).order_by(
        EmailTemplate.timestamp.desc()).first()
    if email_template:
        return jsonify(email_template.to_json())
    else:
        return not_found('Email template not found.')
