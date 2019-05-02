from flask import request, redirect, url_for
from flask_login import current_user
from . import api
from .. import db
from ..models import Review, ReviewComment, ReviewAction
from .authentication import auth
from ..utils.template_convert import gen_token
from .errors import forbidden, bad_request, not_found


@api.route("/comment", methods=['POST'])
# No login required?
def add_comment():
    commenter_id = current_user.id
    review_id = request.json['review_id']
    text = request.json['text']
    comment = ReviewComment(
        commenter_id=commenter_id,
        review_id=review_id,
        text=text
    )
    db.session.add(comment)
    db.session.commit()
    return 'success'


@api.route('/action', methods=['POST'])
@auth.login_required
def add_action():
    commenter_id = current_user.id
    review_id = request.json['review_id']
    action_type = request.json['action_type']
    review = Review.query.get_or_404(review_id)
    if not review:
        return not_found('Target review not found.')
    if (current_user not in review.paper.authors):
        return forbidden('Only authors can vote.')
    existing_action = review.actions.filter_by(
        commenter_id=current_user.id).first()
    if existing_action is None:
        if ReviewAction.add_review_rating(commenter_id=commenter_id,
                                          review_id=review_id,
                                          action=action_type,
                                          medium='Web'):
            return 'Success', 201
        else:
            return bad_request('Operation failed.')
    else:
        return forbidden('Already voted')


@api.route('/action/<action_type>/<int:commenter_id>/<int:review_id>/<token>')
def add_action_email(action_type, token, commenter_id, review_id):
    expected_token = gen_token(commenter_id, review_id)
    if token == expected_token:
        review = Review.query.get_or_404(review_id)
        existing_action = review.actions.filter_by(
            commenter_id=commenter_id).first()
        if existing_action is None:
            if ReviewAction.add_review_rating(commenter_id=commenter_id,
                                              review_id=review_id,
                                              action=action_type,
                                              medium='Email'):
                error_msg = ''
            else:
                error_msg = 'Operation failed.'
        else:
            error_msg = 'You already rated.'
    else:
        error_msg = 'Unauthorized access.'
    return redirect(url_for('main.email_landing', error_msg=error_msg))
