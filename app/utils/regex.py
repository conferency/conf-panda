import re

from wtforms import ValidationError


def check_name(*_name):
    for _n in _name:
        if _n and re.match(r'^[a-zA-Z. \-]+$', _n) is None:
            return False
    return True



def name_validator(form, field):
    if field.data and not check_name(field.data):
        raise ValidationError(
            'Name can only contain letters, dot, slash and space.')
