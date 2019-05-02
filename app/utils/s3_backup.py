import tinys3
from threading import Thread
from flask import current_app


def send_async_file(app, filename):
    with app.app_context():
        AWS_ACCESS_KEY = current_app.config['AWS_ACCESS_KEY']
        AWS_SECRET_KEY = current_app.config['AWS_SECRET_KEY']
        PAPER_BUCKET = current_app.config['PAPER_BUCKET']
        ENDPOINT = current_app.config['S3_ENDPOINT']

        f = open(current_app.config['UPLOADED_PAPERS_DEST'] + filename, 'rb')
        conn = tinys3.Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY,
                                 default_bucket=PAPER_BUCKET, tls=True,
                                 endpoint=ENDPOINT)
        conn.upload(filename, f)


def send_to_s3(filename):
    app = current_app._get_current_object()
    thr = Thread(target=send_async_file, args=[app, filename])
    thr.start()
    return thr
