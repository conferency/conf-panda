from flask import jsonify, request, g, abort, url_for, current_app
from .. import db
from ..models import Todo, Conference
from . import api
from .decorators import permission_required, chair_required
from .errors import forbidden, bad_request
from ..utils.macros import datetime_now_string


@api.route('/todos/<int:todo_id>', methods=['PUT'])
@chair_required
def update_todo_item(todo_id):
    todo = Todo.query.get_or_404(todo_id)
    item = todo.list.get(request.json.get('id'), None)
    if item:
        print item
        item['done'] = request.json['done']
        item['update_timestamp'] = datetime_now_string()
        todo.list[request.json.get('id')] = item
    else:
        return bad_request('Invalid todo item')
    db.session.add(todo)
    db.session.commit()
    return 'Success', 200
