# -*- coding: utf-8 -*-
"""Request log function."""

from flask import current_app, request, session, g
from flask.ext.login import current_user
from threading import Thread
from sqlalchemy.exc import IntegrityError
from ..models import RequestLog
from .. import db
import time


def async_request_log(app, request_log):
    """Support async for event."""
    with app.app_context():
        try:
            db.session.add(request_log)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def add_request(sender, response, **extra):
    """Log conference, submission, review, registration event."""
    # will not log 404 and 405
    if response.status_code not in [301, 404, 405] and 'static' not in request.endpoint and 'api.ping' not in request.endpoint:
        interaction_milli = int((time.time() - g.request_start_time) * 1000)
        if current_user.is_authenticated:
            request_log = RequestLog.add_request_log(request.path,
                                                     request.is_xhr,
                                                     request.blueprint,
                                                     request.endpoint,
                                                     request.view_args,
                                                     request.headers.get('X-Real-IP', request.remote_addr),
                                                     request.user_agent.string,
                                                     request.user_agent.browser,
                                                     request.method, response.status_code,
                                                     request.environ['SERVER_PROTOCOL'],
                                                     interaction_milli,
                                                     request.environ['QUERY_STRING'],
                                                     session['_id'],
                                                     current_user.id,
                                                     real_user_id=session['origin'] if session.get('origin') else None,
                                                     conference_id=current_user.curr_conf_id)
        else:
            request_log = RequestLog.add_request_log(request.path,
                                                     request.is_xhr,
                                                     request.blueprint,
                                                     request.endpoint,
                                                     request.view_args,
                                                     request.headers.get('X-Real-IP', request.remote_addr),
                                                     request.user_agent.string,
                                                     request.user_agent.browser,
                                                     request.method, response.status_code,
                                                     request.environ['SERVER_PROTOCOL'],
                                                     interaction_milli,
                                                     request.environ['QUERY_STRING'])
        app = current_app._get_current_object()
        thr = Thread(target=async_request_log, args=[app, request_log])
        thr.start()
        return thr
    else:
        pass
