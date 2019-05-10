from flask import request, abort
from flask_login import current_user
from .. import db
from . import api
from .authentication import auth


@api.route('/pages/<int:id>', methods=['PUT'])
@auth.login_required
def update_page_content(id):
    page = current_user.curr_conf.site.pages.filter_by(id=id).first()
    if page is None:
        abort(403)
    else:
        i = 0
        page.content = {}
        for section in request.json:
            page.content[str(i)] = section['elements']
            i += 1
        db.session.add(page)
        db.session.commit()
        return 'Success', 200
