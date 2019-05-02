# -*- coding: utf-8 -*-
"""Decorators."""


from functools import wraps
from flask import g
from .errors import forbidden
from ..models import Permission


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.current_user.is_authenticated:
                return forbidden('Insufficient permissions')
            if not g.current_user.can(permission, g.current_user.curr_conf):
                return forbidden('Insufficient permissions')
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def chair_required(f):
    return permission_required(Permission.MANAGE_CONFERENCE)(f)


def admin_required(f):
    return permission_required(0xff)(f)
