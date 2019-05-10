from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import Registration, PromoCode
from . import api
from .errors import forbidden, bad_request
from .authentication import auth
from datetime import datetime
import pytz
# from exceptions import UnicodeDecodeError


def validate_promo_code(promo_json):
    """Validate json in request."""
    if not promo_json['promo_code']:
        raise Exception('Promo code cannot be empty')
    try:
        promo_json['promo_code'].decode('ascii')
    except UnicodeDecodeError:
        raise Exception('Promo code has invalid characters')
    if not promo_json['promo_type'] in ['percentage', 'fixed_amount']:
        raise Exception('Promo code type is invalid')
    if promo_json['promo_currency'] not in ['USD', 'CNY', 'EUR', 'GBP', 'JPY']:
        raise Exception('Promo code currency is invalid')
    try:
        if float(promo_json['promo_value']) < 0:
            raise Exception('Value of promo code ' +
                            promo_json['promo_value'] + '\' is invalid')
    except Exception:
        raise Exception('Promo code value is invalid')
    try:
        if int(promo_json['promo_limit']) < -1:
            raise Exception('Value of usage limits ' +
                            promo_json['promo_limit'] + '\' is invalid')
    except Exception:
        raise Exception('Value of usage limits is invalid')
    try:
        datetime.strptime(
            promo_json['promo_start'], '%Y-%m-%d')
    except Exception:
        raise Exception('Start date \'' + promo_json['promo_start'] +
                        '\' value is invalid')
    try:
        datetime.strptime(
            promo_json['promo_end'], '%Y-%m-%d')
    except Exception:
        raise Exception('Start date \'' + promo_json['promo_end'] +
                        '\' value is invalid')


@api.route('/registrations/<int:registration_id>/promo_codes/<promo_code>')
def check_promo_code(registration_id, promo_code):
    today = datetime.now(pytz.timezone(Registration.query.get_or_404(
        registration_id).conference.timezone)).date()
    promo_code = PromoCode.query.filter(
        PromoCode.registration_id == registration_id,
        PromoCode.promo_code == promo_code).first()
    if promo_code:
        if promo_code.quantity != -1 and \
                promo_code.quantity <= promo_code.usage:
            return bad_request('The promo code has been used up.')
        if promo_code.status != 'Active' or promo_code.start_date > today or \
                promo_code.end_date < today:
            return bad_request('The promo code has expired.')
        return jsonify({
            'id': promo_code.id,
            'promo_code': promo_code.promo_code,
            'type': promo_code.type,
            'value': promo_code.value,
            'currency': promo_code.currency})
    else:
        return bad_request('The promo code is invalid.')


@api.route(
    '/registrations/<int:registration_id>/promo_codes_id/<promo_code_id>')
def get_promo_code(registration_id, promo_code_id):
    """Return promo code info."""
    if promo_code_id != 'undefined':
        promo_code = Registration.query.get_or_404(
            registration_id).promo_codes.filter_by(
            id=promo_code_id).first()
        if promo_code:
            if promo_code.status != 'Active':
                return bad_request('The promo code has expired.')
            return jsonify(promo_code.to_json())
    return 'Cannot find valid promo code.', 204


@api.route('/registrations/<int:registration_id>/promo_codes',
           methods=['POST'])
@auth.login_required
def add_promo_code(registration_id):
    """Add promocode."""
    registration = Registration.query.get_or_404(registration_id)
    if not current_user.is_chair(registration.conference):
        return forbidden('Not allowed')
    try:
        validate_promo_code(request.json)
    except Exception as e:
        return bad_request(e.message)
    if not PromoCode.query.filter_by(promo_code=request.json['promo_code'],
                                     registration_id=registration.id).first():
        promo_code = PromoCode(
            promo_code=str(request.json['promo_code']),
            type=request.json['promo_type'],
            value=float(request.json['promo_value']),
            currency=str(request.json['promo_currency']),
            quantity=int(request.json['promo_limit']),
            start_date=datetime.strptime(
                request.json['promo_start'], "%Y-%m-%d").date(),
            end_date=datetime.strptime(
                request.json['promo_end'], "%Y-%m-%d").date(),
            registration_id=registration.id)
        try:
            db.session.add(promo_code)
            db.session.commit()
        except Exception as e:
            return bad_request(e.message)
        return jsonify(promo_code.to_json()), 201
    else:
        return bad_request('Promo code must be unique')


@api.route('/registrations/<int:registration_id>/promo_codes',
           methods=['PUT'])
@auth.login_required
def update_promo_code(registration_id):
    """Update promo code."""
    registration = Registration.query.get_or_404(registration_id)
    if not current_user.is_chair(registration.conference):
        return forbidden('Not allowed')
    if not request.json.get('promo_code_id', None):
        return bad_request('Invalid promo code id.')
    promo_code = registration.promo_codes.filter_by(
        id=request.json['promo_code_id']).first()
    if not promo_code:
        return bad_request('Invalid promo code.')
    if request.json['action'] == 'disable':
        promo_code.status = 'Inactive'
    elif request.json['action'] == 'enable':
        promo_code.status = 'Active'
    elif request.json['action'] == 'edit':
        try:
            validate_promo_code(request.json['promo_code'])
        except Exception as e:
            return bad_request(e.message)
        promo_code.promo_code = str(request.json['promo_code']['promo_code'])
        promo_code.type = request.json['promo_code']['promo_type']
        promo_code.currency = str(request.json['promo_code']['promo_currency'])
        promo_code.value = float(request.json['promo_code']['promo_value'])
        promo_code.quantity = int(request.json['promo_code']['promo_limit'])
        promo_code.start_date = datetime.strptime(
            request.json['promo_code']['promo_start'], "%Y-%m-%d").date()
        promo_code.end_date = datetime.strptime(
            request.json['promo_code']['promo_end'], "%Y-%m-%d").date()
    else:
        return bad_request('Invalid action')
    try:
        db.session.add(promo_code)
        db.session.commit()
    except Exception as e:
        return bad_request(e.message)
    return jsonify(promo_code.to_json())
