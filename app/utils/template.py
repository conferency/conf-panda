from collections import OrderedDict
from flask import url_for


# from flask.ext.login import current_user
# from ..models import Permission


def generate_navigation_bar(current_user):
    navigation_bar = OrderedDict()
    if current_user.is_administrator():
        navigation_bar["dashboard"] = (
            url_for('conf_admin.admin_dashboard'), 'fa fa-tachometer',
            'Dashboard', None)
        navigation_bar["conferences"] = ('', 'fa fa-list', 'Conferences',
                                         OrderedDict([
                                             ('admin-all-conferences',
                                              (url_for('conf_admin.conference_all'),
                                               'All Conferences')),
                                             ('admin-requests',
                                              (url_for('conf_admin.admin_requests'),
                                               'Conference Requests')),
                                             ('admin-registrations',
                                              (url_for(
                                                  'conf_admin.admin_registrations'),
                                               'Conference Registrations')),
                                             ('admin-conference-pricing',
                                              (url_for(
                                                  'conf_admin.conference_pricing'),
                                               'Conference Pricing'))
                                         ])
                                         )
        navigation_bar['user_search'] = (
            '/user', 'fa fa-search', 'User Directory', None)
        navigation_bar['flask_admin'] = (
            '/admin/', 'fa fa-list', 'Flask Admin', None)
    else:
        navigation_bar["dashboard"] = (
            '/dashboard', 'fa fa-tachometer', 'Dashboard', None)
        navigation_bar["submissions"] = ('', 'fa fa-file-text-o', 'Submissions',
                                         OrderedDict([
                                             ("add-submissions",
                                              (url_for(
                                                  'submission.add_submission'),
                                               'Add Submissions')),
                                             ("my-submissions",
                                              (url_for(
                                                  'submission.my_submissions'),
                                               'My Submissions'))
                                         ])
                                         )
        navigation_bar["reviews"] = ('', 'fa fa-star-o', 'Reviews',
                                     OrderedDict([
                                         ('my-reviews',
                                          (url_for('review.my_reviews'),
                                           'My Reviews')),
                                         ('bidding-reviews',
                                          (url_for('conference.paper_biddings',
                                                   conference_id=current_user.curr_conf_id),
                                           'Review Preferences'))
                                     ])
                                     )
        if current_user.curr_conf_id == 1:
            navigation_bar["reviews"][3].pop('bidding-reviews')
        navigation_bar["conferences"] = ('', 'fa fa-list', 'Conferences',
                                         OrderedDict([
                                             ('my-conferences',
                                              (url_for(
                                                  'conference.my_conference'),
                                               'My Conferences')),
                                             ('my_tickets',
                                              (url_for(
                                                  'main.show_tickets'),
                                               'My Registrations')),
                                             ('all-conferences',
                                              (url_for(
                                                  'conference.all_conference'),
                                               'All Conferences')),
                                             ('request-conferences',
                                              (url_for(
                                                  'conference.request_conference'),
                                               'Conference Requests'))
                                         ])
                                         )
        navigation_bar['connections'] = (
            '/followed-by/' + str(current_user.id), 'fa fa-group',
            'My Connections', None)
        navigation_bar['user_search'] = (
            '/user', 'fa fa-search', 'User Directory', None)

        if current_user.is_chair(current_user.curr_conf):

            # navigation_bar['conferenceWebsite'] = ('/conference/' + str(current_user.curr_conf_id) +'/website', 'fa fa-sitemap', 'Website', None)
            navigation_bar['conferenceRegistration'] = ('', 'fa fa-book', 'Registration',
                                                        OrderedDict([
                                                            ('registration_tickets', (url_for(
                                                                'conference.registration_tickets',
                                                                conference_id=current_user.curr_conf_id), 'Tickets')),
                                                            ('set_registration_form',
                                                             (url_for('conference.set_registration_form',
                                                                      conference_id=current_user.curr_conf_id),
                                                              'Registration Form')),
                                                            ('registration_recent_orders', (url_for(
                                                                'conference.registration_recent_orders',
                                                                conference_id=current_user.curr_conf_id), 'Orders')),
                                                            ('registration_summary',
                                                             (url_for('conference.registration_summary',
                                                                      conference_id=current_user.curr_conf_id),
                                                              'Sales Summary')),
                                                            ('payment_options', (url_for('conference.payment_options',
                                                                                         conference_id=current_user.curr_conf_id),
                                                                                 'Payout')),
                                                            ('set_registration', (url_for(
                                                                'conference.set_registration',
                                                                conference_id=current_user.curr_conf_id),
                                                                                  'Registration Settings')),
                                                        ])
                                                        )
            # navigation_bar['website'] = (url_for('website.website_builder'), 'fa fa-sitemap', 'Website', None
            #  OrderedDict([
            #      ('index', (url_for(
            #          'website.page', page_id=current_user.curr_conf.site.pages.all()[0].id), 'Index'))
            #  ])
            # )

            navigation_bar['conferenceManagement'] = ('', 'fa fa-cogs', 'Administration',
                                                      OrderedDict([
                                                          #   ('conference_summary', (url_for('conference.conference_summary',
                                                          # conference_id=current_user.curr_conf_id),
                                                          # 'Conference
                                                          # Summary')),
                                                          ('submission_menu', ('', 'Submission', OrderedDict([
                                                              ('all-submissions', (url_for(
                                                                  'conference.conference_submission',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                   'All Submissions')),
                                                              ('submission-add', (url_for(
                                                                  'conference.conference_submission_add',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                  'Add Submission')),
                                                              ('submission-form', (url_for(
                                                                  'conference.conference_submission_form',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                   'Submission Form')),
                                                              ('submissions-setting', (url_for(
                                                                  'conference.conference_submission_setting',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                       'Submission Settings')),
                                                          ])
                                                                               )),
                                                          ('review_menu', ('', 'Review', OrderedDict([
                                                              ('all-reviews', (url_for('conference.conferences_review',
                                                                                       conference_id=current_user.curr_conf_id),
                                                                               'All Reviews')),
                                                              ('manual-assignment',
                                                               (url_for('conference.conferences_assignment_manual',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Review Assignments')),
                                                              ('review_request_list',
                                                               (url_for('conference.review_request_list',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Sub-review Requests')),
                                                              ('review-decision',
                                                               (url_for('conference.conferences_decision_review',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Review Decisions')),
                                                              ('review-form',
                                                               (url_for('conference.conference_review_form',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Review Form')),
                                                              ('review-setting',
                                                               (url_for('conference.conference_review_setting',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Review Settings')),
                                                          ])
                                                                           )),
                                                          ('member_menu', ('', 'Member', OrderedDict([
                                                              ('conference-member',
                                                               (url_for('conference.conferences_members',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Conference Members')),
                                                              ('track-member', (url_for(
                                                                  'conference.track_members',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                'Track Members')),
                                                          ])
                                                                           )),
                                                          ('invitation_menu', ('', 'Invitation', OrderedDict([
                                                              ('conference-invitations',
                                                               (url_for('conference.send_invitations',
                                                                        conference_id=current_user.curr_conf_id),
                                                                'Conference Invitation')),
                                                              ('track-invitations', (url_for(
                                                                  'conference.track_send_invitations',
                                                                  conference_id=current_user.curr_conf_id),
                                                                                     'Track Invitation')),
                                                          ])
                                                                               )),
                                                          ('notification_menu', ('', 'Notification', OrderedDict([
                                                              ('notifications', (url_for(
                                                                  'conference.send_notification',
                                                                  conference_id=current_user.curr_conf_id,
                                                                  operation='author'), 'Contact Authors')),
                                                              ('notification-contact-pc', (url_for(
                                                                  'conference.send_notification',
                                                                  conference_id=current_user.curr_conf_id,
                                                                  operation='pc'), 'Contact PC Members')),
                                                              ('notification-contact-member', (url_for(
                                                                  'conference.send_notification',
                                                                  conference_id=current_user.curr_conf_id,
                                                                  operation='member'), 'Contact All Members')),
                                                              ('notification-contact-session', (url_for(
                                                                  'conference.send_notification',
                                                                  conference_id=current_user.curr_conf_id,
                                                                  operation='session'), 'Contact Speakers, Moderators, Discussants'))
                                                          ])
                                                                                 )),
                                                          #   ('notify', (url_for(
                                                          #       'conference.send_notification', conference_id=current_user.curr_conf_id), 'Notifications')),
                                                          ('tracks', (url_for(
                                                              'conference.tracks',
                                                              conference_id=current_user.curr_conf_id), 'Tracks')),
                                                          ('schedule', (url_for(
                                                              'conference.schedule',
                                                              conference_id=current_user.curr_conf_id), 'Schedule')),
                                                          ('proceedings', (url_for('conference.proceedings',
                                                                                   conference_id=current_user.curr_conf_id),
                                                                           'Proceedings')),
                                                          ('reports', (url_for('conference.reports',
                                                                               conference_id=current_user.curr_conf_id),
                                                                       'Reports')),
                                                          ('logs', (url_for('conference.logs',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'Logs')),
                                                          #   ('website_manage', (url_for('conference.website_management',
                                                          #                               conference_id=current_user.curr_conf_id), 'Website')),
                                                          ('setting', (url_for('conference.conferences_setting',
                                                                               conference_id=current_user.curr_conf_id),
                                                                       'Settings')),
                                                          ('payment', (url_for('conference.payment',
                                                                               conference_id=current_user.curr_conf_id),
                                                                       'Plan' if current_user.curr_conf.type == 'Enterprise' else 'Upgrade Plan'))
                                                      ])
                                                      )
        else:
            # if current_user.can(0x02, current_user.curr_conf):
            #     navigation_bar['conferenceWebsite'] = ('', 'fa fa-sitemap', 'Website',
            #                                             OrderedDict([
            #                                                 ('website_manage', (url_for(
            #                                                     'website.management', conference_id=current_user.curr_conf_id), 'Manage Website'))
            #                                             ])
            #                                             )
            if current_user.can(0x04, current_user.curr_conf):
                navigation_bar['conferenceRegistration'] = ('', 'fa fa-book', 'Registration',
                                                            OrderedDict([
                                                                ('registration_summary',
                                                                 (url_for('conference.registration_summary',
                                                                          conference_id=current_user.curr_conf_id),
                                                                  'Sales Summary')),
                                                                ('registration_recent_orders', (url_for(
                                                                    'conference.registration_recent_orders',
                                                                    conference_id=current_user.curr_conf_id),
                                                                                                'Orders')),
                                                                ('set_registration_form',
                                                                 (url_for('conference.set_registration_form',
                                                                          conference_id=current_user.curr_conf_id),
                                                                  'Registration Form')),
                                                                ('payment_options',
                                                                 (url_for('conference.payment_options',
                                                                          conference_id=current_user.curr_conf_id),
                                                                  'Payout')),
                                                                ('set_registration', (url_for(
                                                                    'conference.set_registration',
                                                                    conference_id=current_user.curr_conf_id),
                                                                                      'Registration Settings')),
                                                            ])
                                                            )
            if current_user.can((0x18 | 0x10), current_user.curr_conf):
                navigation_bar['conferenceManagement'] = ('', 'fa fa-cogs',
                                                          'Administration',
                                                          OrderedDict([
                                                              ('submission_menu', ('', 'Submission', OrderedDict([
                                                                  ('all-submissions', (url_for(
                                                                      'conference.conference_submission',
                                                                      conference_id=current_user.curr_conf_id),
                                                                                       'All Submissions')),
                                                                  ('submission-add', (url_for(
                                                                      'conference.conference_submission_add',
                                                                      conference_id=current_user.curr_conf_id),
                                                                                      'Add Submission')),
                                                                  # ('submission-form', (url_for(
                                                                  #     'conference.conference_submission_form', conference_id=current_user.curr_conf_id), 'Submission Form')),
                                                                  ('submissions-setting', (url_for(
                                                                      'conference.conference_submission_setting', conference_id=current_user.curr_conf_id), 'Submission Settings')),
                                                              ])
                                                                                   )),
                                                              ('review_menu', ('', 'Review', OrderedDict([
                                                                  ('all-reviews',
                                                                   (url_for('conference.conferences_review',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'All Reviews')),
                                                                  ('manual-assignment',
                                                                   (url_for('conference.conferences_assignment_manual',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'Review Assignments')),
                                                                  ('review_request_list',
                                                                   (url_for('conference.review_request_list',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'Sub-review Requests')),
                                                                  ('review-decision',
                                                                   (url_for('conference.conferences_decision_review',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'Review Decisions')),
                                                                  # ('review-form', (url_for('conference.conference_review_form',
                                                                  #                          conference_id=current_user.curr_conf_id), 'Review Form')),
                                                                  ('review-setting', (url_for('conference.conference_review_setting',
                                                                                              conference_id=current_user.curr_conf_id), 'Review Settings')),
                                                              ])
                                                                               )),
                                                              ('member_menu', ('', 'Member', OrderedDict([
                                                                  ('track-member', (url_for(
                                                                      'conference.track_members',
                                                                      conference_id=current_user.curr_conf_id),
                                                                                    'Track Members')),
                                                              ])
                                                                               )),
                                                              ('invitation_menu', ('', 'Invitation', OrderedDict([
                                                                  ('track-invitations',
                                                                   (url_for('conference.track_send_invitations',
                                                                            conference_id=current_user.curr_conf_id),
                                                                    'Track Invitation')),
                                                              ])
                                                                                   )),
                                                              ('notification_menu', ('', 'Notification', OrderedDict([
                                                                  ('notifications', (url_for(
                                                                      'conference.send_notification',
                                                                      conference_id=current_user.curr_conf_id,
                                                                      operation='author'), 'Contact Authors')),
                                                                  ('notification-contact-pc', (url_for(
                                                                      'conference.send_notification',
                                                                      conference_id=current_user.curr_conf_id,
                                                                      operation='pc'), 'Contact PC Members')),
                                                              ])
                                                                                     ))
                                                          ])
                                                          )
        if current_user.curr_conf_id == 1:
            navigation_bar['submissions'][3].pop('add-submissions')
            # navigation_bar['reviews'][3].pop('add-reviews')
    return navigation_bar
