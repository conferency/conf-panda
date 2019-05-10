# import json
from threading import Thread
import time
import random
from flask import current_app, render_template, jsonify
from flask_mail import Message
from celery.execute import send_task
from .. import mail
# temp
from .template_convert import template_convert
from .event_log import add_event
from collections import OrderedDict


def send_async_email(app, msg):
    with app.app_context():
        time.sleep(random.uniform(0.05, 5))
        mail.send(msg)
        # task = send_task('worker.send_email', [msg])
        # print task
        # print jsonify({'task_id': task.id})


def send_email(to, subject, template, test_email=False, reply_to=None,
               **kwargs):
    """Send email function."""
    app = current_app._get_current_object()
    msg = Message(subject,
                  sender=app.config['CONF_MAIL_SENDER'], recipients=[to],
                  reply_to=reply_to)
    msg.body = render_template(
        template + '.txt', test_email=test_email, **kwargs)
    msg.html = render_template(
        template + '.html', test_email=test_email, **kwargs)
    # with app.app_context():
    #     mail.send(msg)
    # msg = {}
    # msg['recipient'] = to
    # msg['subject'] = subject
    # msg['html'] = render_template(
    #     template + '.html', test_email=test_email, **kwargs)
    # msg['text'] = render_template(
    #     template + '.html', test_email=test_email, **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


def send_emails_to_authors(app, conference, papers, authors, operation, form):
    pass
    # with app.app_context():
    #     for index, paper in enumerate(papers):
    #         if paper.id in form.paper_ids.data:
    #             for author in authors[index]:
    #                 content = template_convert(
    #                     form.email_content.data, operation, author)
    #                 send_email(author.email,
    #                            form.email_subject.data,
    #                            'email/notification_authors',
    #                            reply_to=conference.contact_email,
    #                            content=content,
    #                            conference=conference, user=author)
    #                 add_event('Send email to ' + author.full_name,
    #                           OrderedDict(
    #                               [('Subject',
    #                                 form.email_subject.data),
    #                                ('Content', content)]),
    #                           conference_id=conference.id,
    #                           type='notification_author')
