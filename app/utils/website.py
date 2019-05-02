from copy import deepcopy
from flask_login import current_user
from flask import request, current_app

from app import db
from ..models import Conference
from itsdangerous import JSONWebSignatureSerializer as Serializer
import requests
import json


def wordpress_generate_data(message):
    domain = request.host
    message['conferency_domain'] = domain
    return Serializer('conferencyinwp').dumps(message)


# def get_wordpress_login_url():
#     message = {'user_id': str(current_user.id),
#                "conf_id": str(current_user.curr_conf_id)}
#     return 'http://' + Conference.query.filter_by(id=current_user.curr_conf_id).first().short_name + '.conferency.com/api/conferency/login?data=&data=' + wordpress_generate_data(message)

def wordpress_create_site(conf):
    print("Trying to activate WordPress for conference id " + str(conf.id) + " using server " + current_app.config['CONF_WORDPRESS_DOMAIN'])
    msg = {}

    message = {'conf_id': conf.id}
    message = wordpress_generate_data(message)
    url = current_app.config['CONF_WORDPRESS_DOMAIN'] +\
          '/api/conferency/create?data=&data=' + message
    print(url)
    s = requests.session()
    s.trust_env = False
    result = s.get(url)
    try:
        result = json.loads(result.text)
    except:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result.text
        return msg

    if result['message'] == 'Success':
        configuration = deepcopy(conf.configuration)
        configuration['wordpress_activation'] = True
        configuration['wordpress_blog_id'] = result['data']['blog_id']
        configuration['wordpress_user_password'] = result['data']['password']
        conf.configuration = configuration
        conf.website = conf.short_name + ".conferency.com"

        db.session.add(conf)
        db.session.commit()
        msg['status'] = 'Success'
        msg['code'] = 200
        msg['result'] = result
        return msg
    else:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result
        msg['data'] = message
        return msg


def wordpress_update_contact(conf):
    print("Trying to update contact of WordPress site for conference id " + str(conf.id))
    msg = {}

    message = {'conf_id': str(conf.id)}
    message = wordpress_generate_data(message)
    url = current_app.config['CONF_WORDPRESS_DOMAIN'] +\
          '/api/conferency/update_contact?data=&data=' + message
    s = requests.session()
    s.trust_env = False
    result = s.get(url)
    try:
        result = json.loads(result.text)
    except:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result.text
        return msg

    if result['message'] == 'Success':
        msg['status'] = 'Success'
        msg['code'] = 200
        msg['result'] = result
        return msg
    else:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result
        msg['data'] = message
        return msg


def wordpress_deactivate_site(conf):
    print("Trying to deactivate WordPress site for conference id " + str(conf.id))
    msg = {}

    message = {'conf_id': str(conf.id)}
    message = wordpress_generate_data(message)
    url = current_app.config['CONF_WORDPRESS_DOMAIN'] +\
          '/api/conferency/deactivate?data=&data=' + message
    s = requests.session()
    s.trust_env = False
    result = s.get(url)
    try:
        result = json.loads(result.text)
    except:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result.text
        return msg

    if result['message'] == 'Success':
        msg['status'] = 'Success'
        msg['code'] = 200
        msg['result'] = result
        return msg
    else:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result
        msg['data'] = message
        return msg


def wordpress_reactivate_site(conf):
    print("Trying to re-activate WordPress site for conference id " + str(conf.id))
    msg = {}

    message = {'conf_id': str(conf.id)}
    message = wordpress_generate_data(message)
    url = current_app.config['CONF_WORDPRESS_DOMAIN'] +\
          '/api/conferency/reactivate?data=&data=' + message
    s = requests.session()
    s.trust_env = False
    result = s.get(url)
    try:
        result = json.loads(result.text)
    except:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result.text
        return msg

    if result['message'] == 'Success':
        conf.website = conf.short_name + ".conferency.com"

        db.session.add(conf)
        db.session.commit()

        msg['status'] = 'Success'
        msg['code'] = 200
        msg['result'] = result
        return msg
    else:
        msg['status'] = 'Failure'
        msg['code'] = 502
        msg['result'] = result
        msg['data'] = message
        return msg

