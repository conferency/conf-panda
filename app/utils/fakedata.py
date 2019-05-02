# -*- coding: utf-8 -*-
import os
import random
from .. import db
from .. import APP_STATIC
from sqlalchemy.exc import IntegrityError
from datetime import datetime, date
from flask import json
from collections import OrderedDict
from ..models import User, Conference, Track, ConferencePayment, Ticket, \
    Role, Author, Paper, PaperStatus, UserDoc, Review, TicketTransaction, \
    TransactionStatus, PaperSession, Session, ConferenceAddon, Post, \
    TicketPrice


# Generate random fake users, default to 50
def generate_fake_users(count=50):
    """Deprecated function."""
    from random import seed
    import forgery_py
    j = 0  # success count
    seed()
    fake_countries = ['United States', 'China', 'Japan']
    icis2015 = Conference.query.filter_by(short_name='icis2015').first()
    for i in range(count):
        u = User(email=forgery_py.internet.email_address(),
                 first_name=forgery_py.name.first_name(),
                 last_name=forgery_py.name.last_name(),
                 password=forgery_py.lorem_ipsum.word(),
                 confirmed=True,
                 organization=forgery_py.name.company_name(),
                 location=forgery_py.address.city(),
                 country=random.choice(fake_countries),
                 about_me=forgery_py.lorem_ipsum.sentence(),
                 member_since=forgery_py.date.date(True))
        db.session.add(u)
        u.join_conference(icis2015)
        try:
            db.session.commit()
            j += 1
        except IntegrityError:
            db.session.rollback()
    print "successfully created " + str(j) + " fake users"


def generate_one_fake_users():
    from random import seed
    import forgery_py
    seed()
    fake_countries = ['United States', 'China', 'Japan']
    u = User(email=forgery_py.internet.email_address(),
             first_name=forgery_py.name.first_name(),
             last_name=forgery_py.name.last_name(),
             password=forgery_py.lorem_ipsum.word(),
             confirmed=True,
             organization=forgery_py.name.company_name(),
             location=forgery_py.address.city(),
             country=random.choice(fake_countries),
             about_me=forgery_py.lorem_ipsum.sentence(),
             member_since=forgery_py.date.date(True))
    db.session.add(u)
    try:
        db.session.commit()
        return u
    except IntegrityError:
        db.session.rollback()
        return None


# Generate site admin for production
def generate_admin():
    admin = User(email="support@conferency.com",
                 first_name="Don",
                 last_name="Draper",
                 password="temp",
                 confirmed=False,
                 organization="Conferency",
                 location="Newark",
                 country="United States",
                 about_me="I am the super admin of Conferency :)")
    db.session.add(admin)
    db.session.commit()
    # assign admin of Conferency
    main_conf = Conference.query.filter_by(name='Main').first()
    admin_role = Role.query.filter_by(name="Administrator").first()
    # update role in conference
    admin.update_conference_role(main_conf, role=admin_role)

    print "successfully created site admin"


def generate_fake(count=100):
    from random import seed, randint
    import forgery_py

    seed()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1, 5)),
                 timestamp=forgery_py.date.date(True),
                 author=u)
        db.session.add(p)
        db.session.commit()


def generate_fake_confs(count, email):
    from random import seed, randint
    import forgery_py

    j = 0  # success count
    seed()
    fake_countries = ["United States"]
    for i in range(count):
        c = Conference(name=forgery_py.forgery.lorem_ipsum.title(randint(10, 18)),
                       short_name=forgery_py.forgery.lorem_ipsum.title(randint(5, 7)),
                       website=forgery_py.internet.domain_name(),
                       contact_email=email,
                       requester_id=3,
                       contact_phone=forgery_py.forgery.address.phone(),
                       address=forgery_py.address.street_address(),
                       city=forgery_py.address.city(),
                       state=forgery_py.address.state(),
                       country=random.choice(fake_countries),
                       start_date=forgery_py.date.date(True),
                       end_date=forgery_py.date.date(),
                       timezone='US/Central',
                       info=forgery_py.forgery.lorem_ipsum.paragraph(sentences_quantity=randint(10, 20)),
                       tags=forgery_py.forgery.lorem_ipsum.words(randint(5, 10)),
                       subjects=forgery_py.forgery.lorem_ipsum.words(randint(5, 10)))
        db.session.add(c)
        try:
            db.session.commit()
            j += 1
        except IntegrityError:
            db.session.rollback()

    print "successfully created " + str(j) + " fake conferences"


def generate_main_conf():
    # main conference should not viewed by any user. So its status is
    # 'Hide' that different from 'Approved' or 'Denied'
    main_conference = Conference(name='Main', short_name='main', status='Hide')
    db.session.add(main_conference)
    db.session.commit()
    print "successfully created the default main conference"


def generate_test_confs():
    # from sqlalchemy import exc
    # from sqlalchemy.orm.exc import FlushError
    # from random import seed, randint
    import forgery_py
    import datetime

    # icis2015 is Professinal plan and amcis2016 is Enterprise
    icis2015 = Conference.query.filter_by(short_name="icis2015").first()
    if icis2015 is None:
        with open(os.path.join(APP_STATIC, 'json/conferences_testing.json')) as data_file:
            data = json.load(data_file)
        for conference in data:
            # smonth, sday, syear = conference['Start Date'].split('/')
            # emonth, eday, eyear = conference['End Date'].split('/')
            c = Conference(approved_time=forgery_py.date.date(True),
                           name=conference['Conference Name'],
                           short_name=conference['Acronym'].lower(),
                           website=(conference['Website'].replace('http://', '')).replace('https://', ''),
                           contact_email="test@conferency.com",
                           contact_phone="3022334355",
                           requester_id=3,
                           address=conference['Venue'],
                           city=conference['City'],
                           state=conference['State'],
                           country=conference['Country'],
                           start_date=datetime.datetime.strptime(conference['Start Date'].replace('-', ''),
                                                                 '%Y%m%d').date(),
                           end_date=datetime.datetime.strptime(conference['End Date'].replace('-', ''),
                                                               '%Y%m%d').date(),
                           timezone='US/Central',
                           status='Approved',
                           info=conference['Summary'],
                           tags=conference['Tags'],
                           subjects=conference['Subject'],
                           submission_deadline=datetime.datetime.strptime(
                               conference['Submission deadline'].replace('-', ''),
                               '%Y%m%d').date())

            c.configuration['submission_process'] = conference.get(
                'submission_process', True)
            c.configuration['review_process'] = conference.get(
                'review_process', True)
            c.configuration['submissions_notification'] = conference.get(
                'submissions_notification', True)
            c.conference_payment = ConferencePayment()
            # default_track = Track(default=True)
            # c.tracks.append(default_track)
            # db.session.add(default_track)
            # generate fake tracks for certain confs
            if c.short_name == "icis2015":
                c.type = 'Professional'
                track1 = Track(name='Decision Analytics and Support')
                track2 = Track(name='Research Methods and Philosophical Foundations of IS')
                track3 = Track(name='General IS Topics')
                track1.subtracks.append(track3)
                c.tracks.append(track1)
                c.tracks.append(track2)
                c.tracks.append(track3)
                db.session.add(track1)
                db.session.add(track2)
                db.session.add(track3)
                r = c.registration
                r.private_question = OrderedDict(
                    [('0', {'require': True, 'ques_type': 2, 'options': [], 'include': True,
                            'desc': 'Badge Name'}),
                     ('1', {'require': True, 'ques_type': 3, 'options': [], 'include': True,
                            'id': 'def', 'desc': 'Bio'}),
                     ('2', {'require': True, 'ques_type': 0, 'options': ['Yes', 'No'], 'include': True,
                            'desc': 'Are you going to present a paper?'})])
                r.configuration_setting = {'instruction': '', 'questions': []}
                db.session.add(r)
            if c.short_name == "amcis2016":
                c.type = 'Enterprise'
                track1 = Track(name='Managing IS Projects and IS Development')
                track2 = Track(name='Practice-Oriented Research')
                track3 = Track(name='Social Media and Digital Collaborations')
                c.tracks.append(track1)
                c.tracks.append(track2)
                c.tracks.append(track3)
                db.session.add(track1)
                db.session.add(track2)
                db.session.add(track3)
            db.session.add(c)
        db.session.commit()
        print "successfully created testing conferences and tracks"
    else:
        print "testing conferences and tracks already created"


# Generate fake ticket for ICIS2015
def generate_fake_tickets():
    icis2015 = Conference.query.filter_by(short_name="icis2015").first()
    if icis2015 is None:
        print "ICIS2015 does not exist - no tickets created"
    else:
        ticket_academic = Ticket(name="Academic",
                                 price=200,
                                 start_date=date(2000, 1, 1),
                                 end_date=date(2050, 1, 1),
                                 registration_id=icis2015.registration.id)
        price_1 = TicketPrice(currency='USD', amount=200)
        price_2 = TicketPrice(currency='CNY', amount=1300)
        db.session.add(price_1)
        ticket_academic.prices.append(price_1)
        db.session.add(price_2)
        ticket_academic.prices.append(price_2)
        ticket_student = Ticket(name="Student",
                                price=100,
                                start_date=date(2000, 1, 1),
                                end_date=date(2050, 1, 1),
                                registration_id=icis2015.registration.id)
        price_3 = TicketPrice(currency='USD', amount=100)
        db.session.add(price_3)
        ticket_student.prices.append(price_3)
        ticket_industry = Ticket(name="Industry",
                                 price=200,
                                 start_date=date(2000, 1, 1),
                                 end_date=date(2050, 1, 1),
                                 registration_id=icis2015.registration.id)
        price_4 = TicketPrice(currency='USD', amount=200)
        db.session.add(price_4)
        ticket_industry.prices.append(price_4)
        icis2015.registration.status = True

        db.session.add(ticket_academic)
        db.session.add(ticket_student)
        db.session.add(ticket_industry)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    print "successfully created fake tickets"


# Generate named fake users with different roles
def generate_test_users():
    import forgery_py
    chair = User(email="chair@conferency.com",
                 first_name="Stephen",
                 last_name="Curry",
                 password="test",
                 confirmed=True,
                 organization="Golden State Warriors",
                 location=forgery_py.address.city(),
                 country="United States",
                 about_me=forgery_py.lorem_ipsum.sentence(),
                 member_since=forgery_py.date.date(True))

    trackchair = User(email="trackchair@conferency.com",
                      first_name="LeBron",
                      last_name="James",
                      password="test",
                      confirmed=True,
                      organization="Cleveland Cavaliers",
                      location=forgery_py.address.city(),
                      country="United States",
                      about_me=forgery_py.lorem_ipsum.sentence(),
                      member_since=forgery_py.date.date(True))

    pc = User(email="pc@conferency.com",
              first_name=u"Kevin 哈哈",
              last_name="Durant",
              organization=u"Oklahoma City Thunder 再者",
              password="test",
              confirmed=True,
              location=forgery_py.address.city(),
              about_me=forgery_py.lorem_ipsum.sentence(),
              country="United States",
              member_since=forgery_py.date.date(True))

    author = User(email="author@conferency.com",
                  first_name="Chris",
                  last_name="Paul",
                  confirmed=True,
                  password="test",
                  organization=u"Los Angeles Clippers 洛杉矶",
                  location=forgery_py.address.city(),
                  about_me=forgery_py.lorem_ipsum.sentence(),
                  country="United States",
                  member_since=forgery_py.date.date(True))

    admin = User(email="admin@conferency.com",
                 first_name="Kobe",
                 last_name="Bryant",
                 password="test",
                 confirmed=True,
                 organization="Los Angeles Lakers",
                 location="Newark",
                 country="United States",
                 about_me="I am the super admin of Conferency :)",
                 member_since=forgery_py.date.date(True),
                 tour_finished=True)

    db.session.add(admin)
    db.session.add(chair)
    db.session.add(trackchair)
    db.session.add(pc)
    db.session.add(author)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()

    print "successfully created site admin, chair, track chair, pc, and author fake users"
    # assign admin of Conferency
    main_conf = Conference.query.filter_by(name='Main').first()
    admin_role = Role.query.filter_by(name="Administrator").first()
    # update role in conference
    admin.update_conference_role(main_conf, role=admin_role)

    # assign admin and chair to all conferences
    # assign PC and Author to first four conferences
    confs = Conference.query.all()
    # admin_role = Role.query.filter_by(name="Administrator").first()
    chair_role = Role.query.filter_by(name="Chair").first()
    track_chair_role = Role.query.filter_by(name="Track Chair").first()
    pc_role = Role.query.filter_by(name="Program Committee").first()
    user_role = Role.query.filter_by(name="Author").first()

    for conf in confs:
        if conf.id == 1:
            pass
            # admin.join_conference(conf, admin_role)
            # chair.join_conference(conf, user_role)
        else:
            # admin.join_conference(conf, admin_role)
            chair.join_conference(conf, chair_role)
            u = generate_one_fake_users()
            if u:
                u.join_conference(conf, chair_role)
        if 1 < conf.id < 6:
            pc.join_conference(conf, pc_role)
            for i in range(15):
                u = generate_one_fake_users()
                if u:
                    u.join_conference(conf, pc_role)
            author.join_conference(conf, user_role)
            for i in range(55):
                u = generate_one_fake_users()
                if u:
                    u.join_conference(conf, user_role)

    # assign admin of Conferency
    # main_conf = Conference.query.filter_by(name='Main').first()
    # admin.join_conference(main_conf, role=admin_role)

    # assign track chair to four tracks in two different confs
    tracks = Track.query.all()
    trackchair.join_conference(Conference.query.get(2), role=user_role)
    trackchair.join_conference(Conference.query.get(3), role=user_role)
    for track in tracks:
        if track.name in ["Decision Analytics and Support",
                          "Research Methods and Philosophical Foundations of IS",
                          "Managing IS Projects and IS Development",
                          "Practice-Oriented Research"]:
            trackchair.join_track(track, track_chair_role)
            pc.join_track(track, pc_role)
    db.session.commit()


# Generate fake papers, default to 100
def generate_fake_papers(count=100):
    from sqlalchemy.orm.exc import FlushError
    from random import seed, randint
    import forgery_py

    j = 0  # success count
    seed()
    user_count = User.query.count()
    # conf_count = Conference.query.count()

    # get named users and tracks
    # chair(id=2), track chair(id=3), pc(id=3) and author(id=4)
    # 27 tracks in total: id 2-7 are user-created tracks
    # id 1, 8-27 are default track for confs
    chair = User.query.filter_by(email="chair@conferency.com").first()
    trackchair = User.query.filter_by(
        email="trackchair@conferency.com").first()
    pc = User.query.filter_by(email="pc@conferency.com").first()
    author = User.query.filter_by(email="author@conferency.com").first()
    icis2015_track1 = Track.query.filter_by(
        name="Decision Analytics and Support").first()
    icis2015_track2 = Track.query.filter_by(
        name="Research Methods and Philosophical Foundations of IS").first()
    icis2015_track3 = Track.query.filter_by(
        name="General IS Topics").first()
    amcis2016_track1 = Track.query.filter_by(
        name="Managing IS Projects and IS Development").first()
    amcis2016_track2 = Track.query.filter_by(
        name="Practice-Oriented Research").first()
    amcis2016_track3 = Track.query.filter_by(
        name="Social Media and Digital Collaborations").first()
    users = [chair, trackchair, pc, author]
    tracks = [icis2015_track1, icis2015_track2, icis2015_track3,
              amcis2016_track1, amcis2016_track2, amcis2016_track3]
    for i in range(count):  # start creating papers
        # randomly choose a user
        uploader = User.query.offset(randint(0, user_count - 1)).first()
        # create a paper with random uploader, random status
        p = Paper(filename="sample" + str(randint(1, 5)) + ".pdf",
                  uploader_id=uploader.id if i > 10 else author.id,
                  # The first 10 papers are uploaded by author account
                  submitted_time=forgery_py.date.date(True),
                  title=forgery_py.forgery.lorem_ipsum.title(randint(10, 18)),
                  status=[PaperStatus.ACCEPTED, PaperStatus.UNDER_REVIEW, PaperStatus.REJECTED][randint(0, 2)],
                  abstract=forgery_py.forgery.lorem_ipsum.paragraph(sentences_quantity=randint(10, 20)),
                  keywords=forgery_py.forgery.lorem_ipsum.words(randint(5, 10)) + ", "
                           + forgery_py.forgery.lorem_ipsum.words(randint(5, 10)) + ", "
                           + forgery_py.forgery.lorem_ipsum.words(randint(5, 10)))
        doc = UserDoc(filename=p.filename, uploader_id=p.uploader_id)
        p.files.append(doc)
        # assign the first 10 papers to one of the six user-created tracks
        # other papers all submitted to default tracks
        if i <= 10:
            p.add_to_track(tracks[randint(0, 5)])
        else:
            p.add_to_track(Track.query.filter_by(id=randint(8, 27)).first())

        uploader_as_author = Author(user_id=uploader.id,
                                    first_name=uploader.first_name,
                                    last_name=uploader.last_name,
                                    email=uploader.email,
                                    country=uploader.country,
                                    organization=uploader.organization,
                                    website=uploader.website)
        p.authors.append(uploader)
        p.authors_list.append(uploader_as_author)

        # first 15 papers have authors from named users
        # each as 1 - 5 authors

        # prevent from too many papers for only 1 author
        authors_list = []
        if i <= 15:
            num_of_author = randint(1, 5)
            for k in range(num_of_author):
                user = None
                while user is None or user in authors_list:
                    if k == 0:
                        user = users[randint(0, 1)]
                    elif k == 1:
                        user = users[randint(2, 3)]
                    else:  # choose from non-named random user
                        user = User.query.offset(randint(5, user_count - 1)).first()

                author = Author(user_id=user.id,
                                first_name=user.first_name,
                                last_name=user.last_name,
                                email=user.email,
                                country=user.country,
                                organization=user.organization,
                                website=user.website)
                # IMPORTANT: both the following two lines are needed
                p.authors.append(user)
                p.authors_list.append(author)
                authors_list.append(user)
        else:  # other 85 papers have 1-5 random authors
            num_of_author = randint(1, 5)
            for k in range(num_of_author):
                user = None
                while user is None or user in authors_list:
                    user = User.query.offset(randint(5, user_count - 1)).first()
                author = Author(user_id=user.id,
                                first_name=user.first_name,
                                last_name=user.last_name,
                                email=user.email,
                                country=user.country,
                                organization=user.organization,
                                website=user.website)
                # IMPORTANT: both the following two lines are needed
                p.authors.append(user)
                p.authors_list.append(author)
                authors_list.append(user)
        try:
            db.session.add(p)
            db.session.commit()
            j += 1
        except IntegrityError:
            db.session.rollback()
        except FlushError:
            db.session.rollback()
    print "successfully created " + str(j) + " fake papers"


def generate_fake_reviews():
    from random import seed, randint, choice
    import forgery_py

    j = 0  # success count
    seed()

    chair = User.query.filter_by(email="chair@conferency.com").first()
    # icis2015 for chair
    con_paper_query = Conference.query.filter_by(short_name="icis2015").first().papers
    con_paper_count = con_paper_query.count()
    for i in range(2):
        p = con_paper_query.offset(randint(0, con_paper_count - 1)).first()
        p.reviewers.append(chair)  # add user as a reviewer
        db.session.add(p)
        try:
            db.session.commit()
            j += 1
        except IntegrityError:
            db.session.rollback()

    # amcis2016
    con_paper_query = Paper.query.filter_by(
        conference_id=Conference.query.filter_by(short_name="amcis2016").first().id)
    con_paper_count = con_paper_query.count()
    for i in range(2):
        p = con_paper_query.offset(randint(0, con_paper_count - 1)).first()
        p.reviewers.append(chair)  # add user as a reviewer
        db.session.add(p)
        try:
            db.session.commit()
            j += 1
        except IntegrityError:
            db.session.rollback()
    papers = Paper.query.all()
    for p in papers:
        for _ in range(4):
            if not p.conference.pcs:
                break
            u = choice(p.conference.pcs)
            if u not in p.authors and u not in p.reviewers:
                r = Review(timestamp=forgery_py.date.date(True),
                           paper_id=p.id,
                           conference_id=p.conference.id,
                           reviewer_id=u.id,
                           evaluation=randint(1, 5),
                           confidence=randint(1, 5),
                           review_body=forgery_py.forgery.lorem_ipsum.paragraph(sentences_quantity=randint(5, 10)),
                           confidential_comments=forgery_py.forgery.lorem_ipsum.paragraph(
                               sentences_quantity=randint(2, 5))
                           )
                p.reviewers.append(u)  # add user as a reviewer
                db.session.add(r)
                try:
                    db.session.commit()
                    j += 1
                except IntegrityError:
                    db.session.rollback()
    print "successfully created " + str(j) + " fake reviews"


def generate_fake_transactions():
    """Generate_fake_transactions."""
    icis2015 = Conference.query.filter_by(short_name="icis2015").first()
    user1 = User.query.get(2)
    attendee1_info = OrderedDict({
        'First Name': user1.first_name,
        'Last Name': user1.last_name,
        'Email': user1.email,
        'Affiliation': user1.organization,
        'abc': 'Kobe Bryant'
    })
    user2 = User.query.get(3)
    attendee2_info = OrderedDict({
        'First Name': user2.first_name,
        'Last Name': user2.last_name,
        'Email': user2.email,
        'Affiliation': user2.organization,
        'abc': 'Stephen Curry'
    })
    user3 = User.query.get(4)
    attendee3_info = OrderedDict({
        'First Name': user3.first_name,
        'Last Name': user3.last_name,
        'Email': user3.email,
        'Affiliation': user3.organization,
        'abc': 'LeBron James'
    })
    user4 = User.query.get(5)
    attendee4_info = OrderedDict({
        'First Name': user4.first_name,
        'Last Name': user4.last_name,
        'Email': user4.email,
        'Affiliation': user4.organization,
        'abc': 'Kevin Durant'
    })
    user5 = User.query.get(6)
    attendee5_info = OrderedDict({
        'First Name': user5.first_name,
        'Last Name': user5.last_name,
        'Email': user5.email,
        'Affiliation': user5.organization,
        'abc': 'Chris Paul'
    })
    if icis2015 is None:
        print "ICIS2015 does not exist - no tickets created"
    else:
        ticket_academic_1 = TicketPrice.query.filter(
            TicketPrice.ticket_id == 1,
            TicketPrice.currency == 'USD').first()
        ticket_academic_2 = TicketPrice.query.filter(
            TicketPrice.ticket_id == 1,
            TicketPrice.currency == 'CNY').first()
        ticket_student = TicketPrice.query.filter(
            TicketPrice.ticket_id == 2,
            TicketPrice.currency == 'USD').first()
        ticket_industry = TicketPrice.query.filter(
            TicketPrice.ticket_id == 3,
            TicketPrice.currency == 'USD').first()
        icis2015.registration.status = True
        # stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
        # customer = stripe.Customer.create(email=user.email)
        # charge = stripe.Charge.create(customer=customer.id, amount=int(round(ticket_academic.price * 100)), currency='usd', description="Registration for " +  user.first_name + ' ' + user.last_name + " (" + icis2015.name + ")")

        transaction1 = TicketTransaction(
            buyer_id=user1.id,
            registration_id=icis2015.registration.id,
            card_number='424242424242424242',
            billing_street='163 South Main St',
            billing_city='Philadelphia',
            billing_state='PA',
            billing_country='United States',
            billing_zipcode='13982',
            attendee_info=attendee1_info,
            status=TransactionStatus.COMPLETED,
            timestamp=datetime(2016, 2, 2, 3, 3, 3, 3),
            holder_name='Kobe Bryant')
        transaction2 = TicketTransaction(
            buyer_id=user2.id,
            registration_id=icis2015.registration.id,
            card_number='424242424242424242',
            billing_street='3726 Main St',
            billing_city='Akron',
            billing_state='OH',
            billing_country='United States',
            billing_zipcode='10983',
            attendee_info=attendee2_info,
            status=TransactionStatus.COMPLETED,
            timestamp=datetime(2016, 2, 2, 3, 3, 3, 3),
            holder_name='Stephen Curry')
        transaction3 = TicketTransaction(
            buyer_id=user3.id,
            registration_id=icis2015.registration.id,
            card_number='424242424242424242',
            billing_street='2938 Main St',
            billing_city='Akron',
            billing_state='OH',
            billing_country='United States',
            billing_zipcode='38472',
            attendee_info=attendee3_info,
            status=TransactionStatus.COMPLETED,
            timestamp=datetime(2016, 4, 2, 3, 3, 3, 3),
            holder_name='LeBron James')
        transaction4 = TicketTransaction(
            buyer_id=user4.id,
            registration_id=icis2015.registration.id,
            card_number='424242424242424242',
            billing_street='163 South Main St',
            billing_city='Newark',
            billing_state='DE',
            billing_country='United States',
            billing_zipcode='19711',
            attendee_info=attendee4_info,
            status=TransactionStatus.COMPLETED,
            timestamp=datetime(2016, 4, 19, 3, 3, 3, 3),
            holder_name='Kevin Durant')
        transaction5 = TicketTransaction(
            buyer_id=user5.id,
            registration_id=icis2015.registration.id,
            card_number='424242424242424242',
            billing_street='245 Main St',
            billing_city='Winston-Salem',
            billing_state='NC',
            billing_country='United States',
            billing_zipcode='38273',
            attendee_info=attendee5_info,
            status=TransactionStatus.COMPLETED,
            timestamp=datetime(2016, 2, 5, 18, 3, 3, 3),
            holder_name='Chris Paul')
        db.session.add(transaction1)
        db.session.add(transaction2)
        db.session.add(transaction3)
        db.session.add(transaction4)
        db.session.add(transaction5)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        transaction1.add_ticket(ticket_academic_1, 1)
        transaction2.add_ticket(ticket_industry, 1)
        transaction3.add_ticket(ticket_student, 1)
        transaction4.add_ticket(ticket_industry, 1)
        transaction5.add_ticket(ticket_academic_2, 1)
    print "successfully created fake transactions"


def generate_fake_schedule():
    c = Conference.query.filter_by(short_name='icis2015').first()
    # generate four sessions
    s1 = Session(conference_schedule_id=c.conference_schedule.id,
                 type='regular',
                 title='Check-in',
                 start_time=datetime(2017, 9, 9, 9, 0),
                 end_time=datetime(2017, 9, 9, 10, 0),
                 venue='Room 1',
                 description='Check-in')
    db.session.add(s1)
    s2 = Session(conference_schedule_id=c.conference_schedule.id,
                 type='paper',
                 title='Paper discussion',
                 start_time=datetime(2017, 9, 9, 10, 30),
                 end_time=datetime(2017, 9, 9, 11, 30),
                 venue='Room 2',
                 description='Paper discussion')
    s2.speakers.append(User.query.get(33))
    s2.speakers.append(User.query.get(24))
    paper_session_1 = PaperSession(paper_id=c.get_papers.all()[0].id)
    paper_session_1.discussants.append(User.query.get(20))
    paper_session_1.discussants.append(User.query.get(43))
    db.session.add(paper_session_1)
    s2.paper_sessions.append(paper_session_1)
    if len(c.get_papers.all()) > 1:
        paper_session_2 = PaperSession(paper_id=c.get_papers.all()[1].id)
        paper_session_2.discussants.append(User.query.get(22))
        paper_session_2.discussants.append(User.query.get(48))
        db.session.add(paper_session_2)
        s2.paper_sessions.append(paper_session_2)
    s2.moderators.append(User.query.get(3))
    db.session.add(s2)
    s3 = Session(conference_schedule_id=c.conference_schedule.id,
                 type='workshop',
                 title='Workshop',
                 start_time=datetime(2017, 9, 9, 13, 30),
                 end_time=datetime(2017, 9, 9, 15, 30),
                 venue='Room 3',
                 description='Workshop')
    s3.speakers.append(User.query.get(23))
    s3.moderators.append(User.query.get(3))
    db.session.add(s3)
    db.session.commit()
    print 'successfully created fake schedule'


def generate_default_addons():
    professional = ConferenceAddon(
        name='Professional Base Fee',
        price=500.0
    )
    db.session.add(professional)
    enterprise = ConferenceAddon(
        name='Enterprise Base Fee',
        price=5000.0
    )
    db.session.add(enterprise)
    db.session.commit()
