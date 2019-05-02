from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import PaperBidding, Paper
from . import api
from .errors import bad_request, forbidden
from flask_login import login_required


@api.route('/conferences/<int:conference_id>/papers/<int:paper_id>/biddings',
           methods=['POST'])
@login_required
def post_paper_bidding(conference_id, paper_id):
    paper = Paper.query.filter(
        Paper.id == paper_id, Paper.conference_id == conference_id).first()
    if paper:
        if current_user in paper.authors:
            return forbidden('Not allowed')
        paper_bidding = paper.paper_biddings.filter_by(
            user_id=request.json.get('user_id')).first()
        if paper_bidding:
            paper_bidding.bid = request.json.get('bidding')
        else:
            paper_bidding = PaperBidding(paper_id=paper_id,
                                         user_id=request.json.get('user_id'),
                                         bid=request.json.get('bidding'))
        db.session.add(paper_bidding)
        db.session.commit()
        return 'Success', 200
    else:
        return bad_request('Paper not found')


@api.route(
    '/conferences/<int:conference_id>/papers/<int:paper_id>/biddings/<int:review_preferene>',
    methods=['GET'])
@login_required
def get_paper_bidding(conference_id, paper_id, review_preferene):
    paper = Paper.query.filter(
        Paper.id == paper_id, Paper.conference_id == conference_id).first()
    if paper:
        paper_biddings = paper.paper_biddings.filter_by(
            bid=review_preferene).all()
        return jsonify(
            {'users': [
                paper_bidding.user.to_json() for paper_bidding in paper_biddings]})
    else:
        return bad_request('Paper not found')
