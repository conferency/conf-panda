from flask import render_template, redirect, request, url_for, flash, current_app, abort, escape, make_response
from flask.ext.login import login_required, current_user
from Crypto.Cipher import DES
from .forms import SiteActivationForm
from ...models import User, Conference, Permission
from ...utils.decorators import permission_required, chair_required
from ...utils.website import wordpress_generate_data
from . import website
from ... import db
from base64 import b64encode
from urllib import quote_plus
import requests
import json


@website.route('/', methods=['GET', 'POST'])
@chair_required
def website_builder():
    return render_template('website/website_editor.html')


@website.route('/<conf_name>', methods=['GET'])
def site(conf_name):
    conference = Conference.query.filter_by(
        short_name=conf_name.lower(), status='Approved').first()

    return render_template('site/conf/index_temp.html', conference=conference)


@website.route('/login', methods=['GET', 'POST'])
@chair_required
def login_wordpress():
    # conf = Conference.query.get_or_404(current_user.curr_conf_id)
    # if not conf.configuration.get('wordpress_activation'):
    #     return "Conference's Website Not Activated", 403
    #
    # return redirect(get_wordpress_login_url())
    pass


