# -*- coding: utf-8 -*-

from functools import wraps
from flask import abort
from flask.ext.login import current_user
from ..models import Permission


def permission_required(permission):
    """Check user's permission in current conference."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            if not current_user.can(permission, current_user.curr_conf):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# def admin_required(f):
#     # print func
#     def decorator(f):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if not current_user.is_authenticated:
#                 abort(403)
#             if not current_user.is_administrator():
#                 abort(403)
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator

def chair_required(f):
    """Check if current user is chair in current conference."""
    return permission_required(Permission.MANAGE_CONFERENCE)(f)


def admin_required(f):
    """Check if user is administrator."""
    return permission_required(0xff)(f)
