# -*- coding: utf-8 -*-
from flask import Blueprint

conf_admin = Blueprint('conf_admin', __name__)

from . import views
