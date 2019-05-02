# -*- coding: utf-8 -*-
from flask import Blueprint

paper = Blueprint('paper', __name__)

from . import views
