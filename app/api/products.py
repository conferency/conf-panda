from flask import jsonify, request
from flask_login import current_user
from .. import db
from ..models import Product, ProductOption, Conference
from . import api
from .errors import forbidden
from ..utils.macros import product_has_sold
from .authentication import auth


@api.route('/products/options/<int:id>')
def get_product(id):
    product = ProductOption.query.get_or_404(id).product
    return jsonify(product.to_json())


@api.route('/products')
def get_products():
    # deprecate
    pass
    products_info = {'products_info': []}
    # get the option ids trim the last empty one
    for option_id in request.args.get('option_ids').split(',')[:-1]:
        products_info['products_info'].append(
            ProductOption.query.get_or_404(option_id).product.to_json())
    return jsonify(products_info)


@api.route('/products/<int:id>', methods=['PUT'])
@auth.login_required
def update_product(id):
    product = Product.query.get_or_404(id)
    if not current_user.is_chair(product.registration.conference):
        return forbidden('Not allowed')
    if request.json['update'] == 'status':
        product.status = request.json['status']
        for option in product.options.all():
            option.status = request.json['status']
            db.session.add(option)
    db.session.add(product)
    db.session.commit()
    return jsonify(product.to_json())


@api.route('conferences/<int:conference_id>/products', methods=['DELETE'])
@auth.login_required
def delete_products(conference_id):
    conference = Conference.query.get_or_404(conference_id)
    if not current_user.is_chair(conference):
        return forbidden('Not allowed')
    product = conference.registration.products.filter_by(
        id=request.json['delete_ticket_id']).first()
    if product and not product_has_sold(product):
        product.status = 'Deleted'
        db.session.add(product)
    try:
        db.session.commit()
    except:
        return 'Failed', 400
    return 'Succeed', 200
