from flask import render_template, request, jsonify
from . import main


@main.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('error/403.html'), 403


@main.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('error/404.html'), 404


@main.app_errorhandler(413)
def entity_too_large(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'entity too large'})
        response.status_code = 413
        return response
    return render_template('error/413.html'), 413


@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('error/500.html'), 500


@main.app_errorhandler(405)
def method_not_allowed(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'the method is not allowed for the \
                            requested URL.'})
        response.status_code = 405
        return response
    return render_template('error/405.html'), 405
