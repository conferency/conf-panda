# -*- coding: utf-8 -*-

import hashlib
from flask import url_for
from flask.ext.login import current_user
from sqlalchemy import and_, or_
from yattag import Doc, indent
from ..models import Paper, DelegateReview, Session, speaker_session, \
    moderator_session, PaperSession


def gen_token(user_id, review_id):
    return hashlib.sha256(str(user_id) + str(review_id) + 'conf').hexdigest()


def template_convert(content, operation, data, **args):
    if operation == 'author':
        # convert variables in the content
        author = data
        paper = author.paper
        content = content.replace('*TITLE*', paper.title)
        content = content.replace('*STATUS*', paper.status)
        content = content.replace(
            '*NAME*', author.full_name)
        content = content.replace(
            '*FIRST_NAME*', author.first_name)
        content = content.replace(
            '*LAST_NAME*', author.last_name)
        content = content.replace('*CONFERENCE_NAME*',
                                  paper.conference.name)
        content = content.replace('*CONFERENCE_SHORTNAME*',
                                  paper.conference.short_name)
        content = content.replace(
            '*PAPER_REVIEW_SYSTEM*', '<a href="' +
            url_for('auth.login', conf=current_user.curr_conf_id,
                    _external=True, _scheme='https') + '">' +
            url_for('auth.login', conf=current_user.curr_conf_id,
                    _external=True, _scheme='https') + '</a>')
        content = content.replace(
            '*CONFERENCE_WEBSITE*', paper.conference.website)
        # add reviews
        if '*PAPER_REVIEW*' in content:
            reviews = '<div>'
            i = 1
            for review in paper.reviews:
                reviews += '<h4>Review ' + \
                           str(i) + '</h4><p>' + review.review_body + '</p>'
                if paper.conference.configuration['review_feedback']:
                    btn_style = """
                                        style="
                                        background-color: #23c6c8;
                                            border: none;
                                            border-radius: 3px;
                                            color: white;
                                            padding: 5px 10px;
                                            text-align: center;
                                            text-decoration: none;
                                            display: inline-block;
                                            font-size: 14px;"
                                        """
                    reviews += '<h4>Confidential Feedback to Chairs: did you \
                    find the review helpful?</h4>'
                    reviews += ('<a href="%s" ' + btn_style +
                                '>Yes</a>&nbsp;&nbsp;') % url_for(
                        'api.add_action_email',
                        token=gen_token(author.user_id, review.id),
                        action_type='Yes',
                        commenter_id=author.user_id,
                        review_id=review.id,
                        _external=True,
                        _scheme='https')
                    reviews += ('<a href="%s" ' + btn_style +
                                '>No</a>') % url_for(
                                'api.add_action_email',
                                token=gen_token(author.user_id, review.id),
                                action_type='No',
                                commenter_id=author.user_id,
                                review_id=review.id,
                                _external=True,
                                _scheme='https')
                i += 1
            reviews += '</div>'
            content = content.replace('*PAPER_REVIEW*', reviews)
    elif operation == 'pc' or operation == 'member':
        receiver = data
        # generate all the needed paper list containing delegated papers
        # all assigned papers for review
        paper_table = '<div><table class="table table-stripped"><thead><tr>\
            <th>Title</th></tr></thead><tbody>'
        papers_for_review = receiver.get_review_assignments.filter(
            Paper.conference_id == current_user.curr_conf_id).all()
        if '*REVIEW_ASSIGNMENTS*' in content:
            all_assigned_papers_html = paper_table
            for paper in papers_for_review:
                all_assigned_papers_html += '<tr><td>' + paper.title + \
                    '</td></tr>'
            all_assigned_papers_html += '</tbody></table></div>'
            content = content.replace('*REVIEW_ASSIGNMENTS*',
                                      all_assigned_papers_html)
        # all the missing reviewed papers
        if '*MISSING_REVIEWED_PAPERS*' in content:
            papers_with_missing_review = []
            for paper in papers_for_review:
                if paper.reviews.filter_by(
                        reviewer_id=receiver.id).first() is None:
                    papers_with_missing_review.append(paper)
                    if paper.delegated_review_assignment.filter(
                            DelegateReview.delegator_id == receiver.id,
                            DelegateReview.status == 'Approved').first():
                        papers_with_missing_review.remove(paper)
            missing_reviewed_papers_html = paper_table
            for paper in papers_with_missing_review:
                missing_reviewed_papers_html += '<tr><td>' + paper.title + \
                    '</td></tr>'
            missing_reviewed_papers_html += '</tbody></table></div>'
            content = content.replace(
                '*MISSING_REVIEWED_PAPERS*', missing_reviewed_papers_html)
        # all the completed review papers
        if '*REVIEWED_PAPERS*' in content:
            papers_with_complete_review = []
            for paper in papers_for_review:
                if paper.reviews.filter_by(reviewer_id=receiver.id).first():
                    papers_with_complete_review.append(paper)
                elif paper.delegated_review_assignment.filter(
                        DelegateReview.delegator_id == receiver.id,
                        DelegateReview.status == 'Approved').first():
                    papers_with_complete_review.append(paper)
            reviewed_papers_html = paper_table
            for paper in papers_with_complete_review:
                reviewed_papers_html += '<tr><td>' + paper.title + '</td></tr>'
            reviewed_papers_html += '</tbody></table></div>'
            content = content.replace(
                '*REVIEWED_PAPERS*', reviewed_papers_html)
        # replace the content variables
        content = content.replace(
            '*NAME*', receiver.full_name)
        content = content.replace(
            '*FIRST_NAME*', receiver.first_name)
        content = content.replace(
            '*LAST_NAME*', receiver.last_name)
        content = content.replace(
            '*CONFERENCE_WEBSITE*', current_user.curr_conf.website)
        content = content.replace(
            '*CONFERENCE_NAME*', current_user.curr_conf.name)
        content = content.replace(
            '*PAPER_REVIEW_SYSTEM*', '<a href="' +
            url_for('auth.login', conf=current_user.curr_conf_id,
                    _external=True, _scheme='https') + '">' +
            url_for('auth.login',
                    conf=current_user.curr_conf_id, _external=True,
                    _scheme='https') + '</a>')
    elif operation == 'session':
        receiver = data
        content = content.replace(
            '*NAME*', receiver.full_name)
        content = content.replace(
            '*FIRST_NAME*', receiver.first_name)
        content = content.replace(
            '*LAST_NAME*', receiver.last_name)
        content = content.replace(
            '*CONFERENCE_WEBSITE*', current_user.curr_conf.website)
        content = content.replace(
            '*CONFERENCE_NAME*', current_user.curr_conf.name)
        content = content.replace(
            '*SCHEDULE_PAGE_URL*', '<a href="' +
            url_for('main.conf_schedule',
                    conf_name=current_user.curr_conf.short_name,
                    _external=True) + '">' +
            url_for('main.conf_schedule',
                    conf_name=current_user.curr_conf.short_name,
                    _external=True) + '</a>')
        # content = content.replace(
        #     '*APP_DOWNLOAD_LINK*', '<table align="center"><a \
        #     href="https://itunes.apple.com/app/conferency/id1246305811" \
        #     target="_blank" style="margin-right: 5px;">\
        #     <div style="width: 135px; display: inline-block;">\
        #     <img src="https://app.conferency.com/static/img/Download_on_the_App_Store_Badge.svg?q=1518547361" \
        #     style="margin:6%; width:80%; height: auto; max-width: 100%;">\
        #     </div></a><a \
        #     href="https://play.google.com/store/apps/details?id=com.conferency.main" target="_blank">\
        #     <div style="width: 135px; display: inline-block;">\
        #     <img src="https://app.conferency.com/static/img/google-play-badge.png?q=1518547361" style="height: auto; max-width: 100%;">\
        #     </div></a></table>')
        content = content.replace(
            '*APP_DOWNLOAD_LINK*', '<tr><td><table height="35" align="center" \
            valign="middle" border="0" cellpadding="0" cellspacing="0" \
            class="tablet-button" st-button="edit"><tbody><tr>\
            <td width="auto" align="center" valign="middle" height="35" \
            style="><span style="color: #ffffff; font-weight: 300;">\
            <a href="https://itunes.apple.com/app/conferency/id1246305811" \
            target="_blank" style="margin-right: 5px;">\
            <div style="width: 135px; display: inline-block;">\
            <img src="https://app.conferency.com/static/img/Download_on_the_App_Store_Badge.svg?q=1518547361" \
            style="margin:6%; width:80%; height: auto; max-width: 100%;">\
            </div></a><a href="https://play.google.com/store/apps/details?id=com.conferency.main" target="_blank">\
            <div style="width: 135px; display: inline-block;">\
            <img src="https://app.conferency.com/static/img/google-play-badge.png?q=1518547361" style="height: auto; max-width: 100%;">\
            </div></a></span></td></tr></tbody></table></td></tr>'
        )
        send_to = args['send_to']
        conference_schedule_id = current_user.curr_conf.conference_schedule.id
        if send_to == 'checkbox_speakers':
            sessions = receiver.speak_sessions.filter(
                Session.conference_schedule_id == conference_schedule_id,
                Session.status != 'Deleted').all()
        elif send_to == 'checkbox_moderators':
            sessions = receiver.moderator_sessions.filter(
                Session.conference_schedule_id == conference_schedule_id,
                Session.status != 'Deleted').all()
        elif send_to == 'checkbox_discussants':
            paper_sessions = receiver.paper_sessions.filter(
                PaperSession.session_id == Session.id,
                Session.conference_schedule_id == conference_schedule_id,
                Session.status != 'Deleted').all()
            sessions = [
                paper_session.session for paper_session in paper_sessions]
        else:
            sessions = Session.query.filter(
                Session.conference_schedule_id == conference_schedule_id,
                or_(
                    and_(speaker_session.c.user_id == receiver.id,
                         speaker_session.c.session_id == Session.id),
                    and_(moderator_session.c.user_id == receiver.id,
                         moderator_session.c.session_id == Session.id)
                ),
                Session.status != 'Deleted').all()
        # sessions_html = '<div>'
        # for session in sessions:
        #     session_html = '<div class="row">' + '<h4>' + session.title + \
        #         '</h4>' + '<p>' + str(session.start_time) + ' - ' + \
        #         str(session.end_time) + '</p><p>' + session.venue + \
        #         '</p><p>' + session.description + '</p>'
        #     session_html += '</div>'
        #     sessions_html += session_html
        # html = ''
        sessions_html = ''
        for session in sessions:
            doc, tag, text, line = Doc().ttl()
            with tag('div', klass='row'):
                line('h4', session.title)
                line('p', str(session.start_time))
                line('p', str(session.end_time))
                line('p', session.venue)
                line('p', session.description)
            sessions_html += doc.getvalue()
        content = content.replace(
            '*SESSION_INFO*', sessions_html)
        if send_to == 'checkbox_discussants':
            papers = [paper_session.paper for paper_session in paper_sessions]
        else:
            papers = [
                paper for session in sessions for paper in session.papers]
        paper_html = ''
        doc, tag, text, line = Doc().ttl()
        with tag('table'):
            for paper in papers:
                with tag('tr'):
                    line('td', paper.title)
                    with tag('td', ('style', 'padding:0px 15px;')):
                        with tag('a',
                                 # ('style',
                                 #  'background-color:#1ab394;\
                                 #  border-color:#1ab394;color: #FFFFFF;\
                                 #  border-radius:3px;margin:0px 5px;\
                                 #  padding:1px 5px;font-size:12px;'),
                                 href=url_for('paper.get_paper_info',
                                              paper_id=paper.id,
                                              _external=True)):
                            text('Login to check paper information')
        paper_html += doc.getvalue() + \
            '<p>Login using <b>' + receiver.email + '</b></p>'
        content = content.replace(
            '*SESSION_PAPER_INFO*', paper_html)
    return content
