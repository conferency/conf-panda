from flask import request, jsonify
from . import api
from ..models import Conference
from .. import db
from .decorators import admin_required
from ..utils.website import wordpress_deactivate_site
from ..utils.email_operation import send_email
from ..utils.export import generate_csv_response
from datetime import datetime
from .errors import forbidden, bad_request
from copy import deepcopy
from flask_login import current_user
from .authentication import auth


@api.route('/websites/<int:conference_id>/activate')
@auth.login_required
def use_hosted_wordpress(conference_id):
    conf = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conf):
        return forbidden('Not Authenciated.')
    if conf.configuration.get('website_type',
                              'self_hosted') == 'hosted_wordpress':
        return jsonify(message='Not Valid', code=403), 403

    # if conf.configuration.get('wordpress_activation'):
    #     result = wordpress_reactivate_site(conf)
    # else:
    #     result = wordpress_create_site(conf)
    #
    # if result['code'] == 200:
    #     configuration = deepcopy(conf.configuration)
    else:
        configuration = deepcopy(conf.configuration)
        configuration['website_type'] = 'hosted_wordpress'
        conf.configuration = configuration
        db.session.add(conf)
        db.session.commit()
        return 'Success', 200
    #     return jsonify(result)
    # else:
    #     return jsonify(result), 502


@api.route('/websites/<int:conference_id>/wp-password', methods=['PUT'])
@auth.login_required
@admin_required
def update_wp_password(conference_id):
    """Update password for wp."""
    conf = Conference.query.get_or_404(conference_id)
    configuration = deepcopy(conf.configuration)
    configuration['wordpress_user_password'] = request.json['password']
    conf.configuration = configuration
    try:
        db.session.add(conf)
        db.session.commit()
        return 'Success', 200
    except:
        return bad_request('Database error')


@api.route('/websites/<int:conference_id>/self-hosted', methods=['PUT'])
@auth.login_required
def use_self_hosted_site(conference_id):
    conf = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conf):
        return forbidden('Not Authenciated.')
    if not request.json.get('url', False):
        return jsonify(message='Not Valid', code=403), 403

    if conf.configuration.get('wordpress_activation'):
        result = wordpress_deactivate_site(conf)
    else:
        result = {'code': 200, 'status': 'Success'}

    if result['code'] == 200:
        configuration = deepcopy(conf.configuration)
        configuration['website_type'] = 'self_hosted'
        conf.configuration = configuration
        conf.website = request.json['url']

        db.session.add(conf)
        db.session.commit()
        return jsonify(result)
    else:
        return jsonify(result), 502


@api.route('/websites/<int:conference_id>/email_instruction')
@auth.login_required
def email_instruction(conference_id):
    conf = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conf):
        return forbidden('Not Authenciated.')
    if not conf.configuration.get('wordpress_activation', False) or conf.configuration.get('website_type',
                                                                                           'self_hosted') != 'hosted_wordpress':
        return jsonify(message='Not Valid', code=403), 403

    dashboard_url = 'http://' + conf.short_name + '.conferency.com/wp-login.php'
    username = conf.short_name
    password = conf.configuration['wordpress_user_password']

    send_email(current_user.email, 'WordPress Login Instruction',
               'email/website_login', user=current_user, dashboard_url=dashboard_url, username=username,
               password=password)

    return jsonify(message='Success', code=200)


@api.route('/websites/<int:conference_id>/download_instruction')
@auth.login_required
def download_instruction(conference_id):
    conf = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conf):
        return forbidden('Not Authenciated.')
    if not conf.configuration.get('wordpress_activation', False) or conf.configuration.get('website_type',
                                                                                           'self_hosted') != 'hosted_wordpress':
        return jsonify(message='Not Valid', code=403, config=conf.configuration), 403

    dashboard_url = 'http://' + conf.short_name + '.conferency.com/wp-login.php'
    username = conf.short_name
    password = conf.configuration['wordpress_user_password']

    csv_columns = ['Dashboard URL', 'Username', 'Password']
    response = generate_csv_response(csv_columns,
                                     [{'Dashboard URL': dashboard_url, 'Username': username, 'Password': password}],
                                     conf.short_name + '_wordpress_login_' + datetime.today().strftime('%Y-%m-%d'))

    return response
