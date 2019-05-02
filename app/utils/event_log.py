# -*- coding: utf-8 -*-
"""event log function."""


from flask.ext.login import current_user
from threading import Thread
from flask import current_app
from ..models import EventLog
from collections import OrderedDict
from .. import db


def async_event_log(app, event_log):
    """Support async for event."""
    with app.app_context():
        db.session.add(event_log)
        db.session.commit()


def add_event(subject, detail, conference_id=None,
              paper_id=None, review_id=None, type=None, override_user_id=None):
    """Log conference, submission, review, registration event."""
    event_log = EventLog(conference_id=conference_id,
                         user_id=override_user_id or None if
                         current_user.is_anonymous else current_user.id,
                         event=OrderedDict([
                             ('subject', subject),
                             ('detail', detail)
                         ]),
                         paper_id=paper_id,
                         review_id=review_id,
                         type=type)
    app = current_app._get_current_object()
    thr = Thread(target=async_event_log, args=[app, event_log])
    thr.start()
    return thr
