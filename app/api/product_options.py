from flask import jsonify, request, g
from ..models import ProductOption
from . import api

@api.route('/products/options')
def get_product_options():
    # print request.args.get('option_ids').split(',')[:-1]
    product_options_info = {'product_options_info': []}
    # get the option ids trim the last empty one
    for option_id in request.args.get('option_ids', '').split(',')[:-1]:
        product_options_info['product_options_info'].append(
            ProductOption.query.get_or_404(option_id).to_json())
    return jsonify(product_options_info)
