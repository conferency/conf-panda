from ...models import User


def check_author_submission_limit(conference_id, email):
    '''
    '''
    if len(User.query.filter_by(email=email).first().paper.filter_by(
            conference_id=conference_id).all()) > limit:
        return False
    else:
        return True
