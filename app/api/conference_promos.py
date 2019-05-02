from flask import jsonify, request, g
from .. import db
from ..models import ConferencePromoCode
from . import api
from .decorators import admin_required
from .authentication import auth
from datetime import datetime


@api.route('/promo_codes/<promo_code>')
def check_conf_promo_code(promo_code):
    promo_code = ConferencePromoCode.validate_promo_code(promo_code)
    if promo_code:
        if promo_code.quantity != -1 and \
                promo_code.quantity <= promo_code.usage:
            return 'The promo code is inactive', 400
        else:
            return jsonify({
                'id': promo_code.id,
                'promo_code': promo_code.promo_code,
                'type': promo_code.type,
                'value': promo_code.value})
    else:
        return 'The promo code is invalid.', 400


# @api.route('/registrations/<int:registration_id>/promo_codes_id/<promo_code_id>')
# def get_promo_code(registration_id, promo_code_id):
#     if promo_code_id != 'undefined':
#         promo_code = Registration.query.get_or_404(
#             registration_id).promo_codes.filter_by(id=promo_code_id, status='Active').first()
#         return jsonify(promo_code.to_json())
#     else:
#         return 'Promo code is empty', 204


@api.route('/admin/promo_codes', methods=['POST'])
@auth.login_required
@admin_required
def add_conf_promo_code():
    # print request.json
    if not ConferencePromoCode.query.filter_by(
            promo_code=request.json['promo_code']).first():
        promo_code = ConferencePromoCode(
            promo_code=request.json['promo_code'],
            type=request.json['promo_type'],
            value=float(request.json['promo_value']),
            quantity=int(request.json['promo_limit']),
            start_date=datetime.strptime(
                request.json['promo_start'], "%Y-%m-%d").date(),
            end_date=datetime.strptime(
                request.json['promo_end'], "%Y-%m-%d").date())
        try:
            db.session.add(promo_code)
            db.session.commit()
        except Exception as e:
            return e.message, 406
        return jsonify(promo_code.to_json())
    else:
        return 'Promo code must be unique', 400


@api.route('/admin/promo_codes', methods=['PUT'])
@auth.login_required
@admin_required
def update_conf_promo_code():
    # print request.json.get('promo_code')
    promo_code = ConferencePromoCode.query.get_or_404(
        request.json['promo_code_id'])
    if request.json['action'] == 'disable':
        promo_code.status = 'Inactive'
    elif request.json['action'] == 'enable':
        promo_code.status = 'Active'
    elif request.json['action'] == 'edit':
        promo_code.promo_code = request.json['promo_code']['promo_code']
        promo_code.type = request.json['promo_code']['promo_type']
        promo_code.value = float(request.json['promo_code']['promo_value'])
        promo_code.quantity = int(request.json['promo_code']['promo_limit'])
        promo_code.start_date = datetime.strptime(
            request.json['promo_code']['promo_start'], "%Y-%m-%d").date()
        promo_code.end_date = datetime.strptime(
            request.json['promo_code']['promo_end'], "%Y-%m-%d").date()
    try:
        db.session.add(promo_code)
        db.session.commit()
    except Exception as e:
        return e.message, 400
    return jsonify(promo_code.to_json())
