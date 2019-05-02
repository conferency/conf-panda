from flask import jsonify
from . import api
from ..models import Configuration


@api.route('/configurations')
def get_configurations():
    configurations = Configuration.query.all()
    return jsonify(
        {'configurations': [
            configuration.to_json() for configuration in configurations]})
