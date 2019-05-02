from flask import jsonify, request, g
from .. import db
from ..models import ConferenceAddon
from . import api
from .decorators import admin_required
from .authentication import auth


# @api.route('/registrations/<int:registration_id>/promo_codes/<promo_code>')
# def check_promo_code(registration_id, promo_code):
#     today = datetime.now(pytz.timezone(Registration.query.get_or_404(
#         registration_id).conference.timezone)).date()
#     promo_code = PromoCode.query.filter(and_(
#         PromoCode.registration_id == registration_id,
#         PromoCode.promo_code == promo_code, PromoCode.status == 'Active',
#         PromoCode.start_date <= today,
#         PromoCode.end_date >= today
#     )).first()
#     if promo_code:
#         if promo_code.quantity != -1 and promo_code.quantity <= promo_code.usage:
#             return 'The promo code is inactive', 400
#         else:
#             return jsonify({'id': promo_code.id, 'promo_code': promo_code.promo_code, 'type': promo_code.type, 'value': promo_code.value})
#     else:
#         return 'The promo code is invalid. Be aware that the promo code is case-sensitive', 400


# @api.route('/registrations/<int:registration_id>/promo_codes_id/<promo_code_id>')
# def get_promo_code(registration_id, promo_code_id):
#     if promo_code_id != 'undefined':
#         promo_code = Registration.query.get_or_404(
#             registration_id).promo_codes.filter_by(id=promo_code_id, status='Active').first()
#         return jsonify(promo_code.to_json())
#     else:
#         return 'Promo code is empty', 204


# @api.route('/admin/promo_codes', methods=['POST'])
# @admin_required
# def add_conf_promo_code():
#     # print request.json
#     if not ConferencePromoCode.query.filter_by(
#             promo_code=request.json['promo_code']).first():
#         promo_code = ConferencePromoCode(
#             promo_code=request.json['promo_code'],
#             type=request.json['promo_type'],
#             value=float(request.json['promo_value']),
#             quantity=int(request.json['promo_limit']),
#             start_date=datetime.strptime(
#                 request.json['promo_start'], "%Y-%m-%d").date(),
#             end_date=datetime.strptime(
#                 request.json['promo_end'], "%Y-%m-%d").date())
#         try:
#             db.session.add(promo_code)
#             db.session.commit()
#         except Exception as e:
#             return e.message, 406
#         return jsonify(promo_code.to_json())
#     else:
#         return 'Promo code must be unique', 400


@api.route('/admin/addon', methods=['PUT'])
@auth.login_required
@admin_required
def update_conf_addon():
    addon = ConferenceAddon.query.get_or_404(
        request.json['addon_id'])
    addon.price = float(request.json['price'])
    # if request.json['action'] == 'disable':
    #     promo_code.status = 'Inactive'
    # elif request.json['action'] == 'enable':
    #     promo_code.status = 'Active'
    # elif request.json['action'] == 'edit':
    #     promo_code.promo_code = request.json['promo_code']['promo_code']
    #     promo_code.type = request.json['promo_code']['promo_type']
    #     promo_code.value = float(request.json['promo_code']['promo_value'])
    #     promo_code.quantity = int(request.json['promo_code']['promo_limit'])
    #     promo_code.start_date = datetime.strptime(
    #         request.json['promo_code']['promo_start'], "%Y-%m-%d").date()
    #     promo_code.end_date = datetime.strptime(
    #         request.json['promo_code']['promo_end'], "%Y-%m-%d").date()
    try:
        db.session.add(addon)
        db.session.commit()
    except Exception as e:
        return e.message, 400
    # return jsonify(addon.to_json())
    return 'Success', 200
