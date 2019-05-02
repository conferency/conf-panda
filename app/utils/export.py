# -*- coding: utf-8 -*-
"""Functions to generate texts."""

from flask import Response
import cStringIO
import unicodecsv as csv
from bs4 import BeautifulSoup


def generate_csv_response(columns, rows, file_name):
    """Generate csv file."""
    csv_str = cStringIO.StringIO()
    csv_str.write(u'\ufeff'.encode('utf-8'))
    write = csv.writer(csv_str, dialect='excel', encoding='utf-8')
    try:
        write.writerow(columns)
        for row in rows:
            row_list = []
            for column in columns:
                row_list.append(row.get(column, '').encode('utf-8') if
                                isinstance(row.get(column, ''), basestring)
                                else str(row.get(column)))
            write.writerow(row_list)
    except Exception as e:
        raise e
    if '.csv' == file_name[-4:]:
        file_name = file_name[:-4]
    response = Response(csv_str.getvalue(),
                        mimetype='text/csv',
                        headers={'Content-disposition':
                        'attachment; filename=' + file_name + '.csv'})
    return response


def generate_txt_response(columns, rows, file_name):
    """Generate txt file."""
    try:
        txt_str = cStringIO.StringIO()
        for row in rows:
            if row.get('Paper ID'):
                txt_str.writelines('\n' + '********************' * 4 + '\n')
            elif row.get('Reviewer'):
                txt_str.writelines('++++++++++++++++++++' * 4 + '\n')
            for column in columns:
                if row.get(column):
                    txt_str.writelines(
                        column + ': ' + (row.get(column).encode('utf-8') if
                                         isinstance(row.get(column, ''),
                                                    basestring)
                                         else str(row.get(column))) +
                        '\n')

        if ".txt" == file_name[-4:]:
            file_name = file_name[:-4]
        response = Response(txt_str.getvalue(),
                            mimetype='text/plain',
                            headers={'Content-disposition':
                            'attachment; filename=' + file_name + '.txt'})
        return response
    except Exception as e:
        raise e


def strip_html(text):
    """Strip html tags in text."""
    return BeautifulSoup(text, 'html.parser').get_text()
