import unittest
from flask import url_for
from app import create_app
from flask.ext.login import current_user
from app.models import Product


class ProductTestCase(unittest.TestCase):
    product_1 = {
        '_method': 'post',
        'product_name': 'Tour pass',
        'product_inventory': '-1',
        'product_price': '100',
        'product_currency': 'USD'
    }

    product_2 = {
        '_method': 'post',
        'product_name': 'T shirt',
        'product_inventory': '-1',
        'product_price': '20',
        'product_currency': 'USD',
        'new_option_name_0': 'XL',
        'new_option_price_0': '25',
        'new_option_name_1': 'L',
        'new_option_price_1': '20'
    }

    product_1_edit = {
        'product_id': '',
        '_method': 'put',
        'product_name': 'Tour pass',
        'product_inventory': '-1',
        'product_price': '600',
        'product_currency': 'CNY'
    }

    product_2_edit = {
        'product_id': '',
        '_method': 'put',
        'product_name': 'T shirt',
        'product_inventory': '-1',
        'product_price': '20',
        'product_currency': 'USD',
        # 'option_name_1': 'XL',
        # 'option_price_1': '25',
        # 'option_name_2': 'L',
        # 'option_price_2': '25',
        'new_option_name_0': 'M',
        'new_option_price_0': '20'
    }

    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test1_add_products(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")
            current_user.set_conference_id(2)

            response = c.get(url_for('conference.registration_products',
                                     conference_id=2))
            self.assertTrue(
                response.status_code == 200, msg='Add products ICIS2015')
            # add products
            response = c.post(url_for('conference.registration_products',
                                      conference_id=2),
                              data=self.product_1,
                              follow_redirects=True)
            self.assertTrue('Success' in response.get_data(as_text=True))
            product_1 = Product.query.filter_by(name='Tour pass').first()
            self.assertTrue(product_1, msg='add product 1')
            self.product_1_edit['product_id'] = str(product_1.id)
            response = c.post(url_for('conference.registration_products',
                                      conference_id=2),
                              data=self.product_2,
                              follow_redirects=True)
            self.assertTrue('Success' in response.get_data(as_text=True))
            product_2 = Product.query.filter_by(name='T shirt').first()
            self.assertTrue(product_2, msg='add product 2')
            self.product_2_edit['product_id'] = str(product_2.id)
            product_2_op_1 = product_2.options.filter_by(
                option_name='XL').first()
            self.product_2_edit['option_name_' + str(product_2_op_1.id)] = 'XL'
            self.product_2_edit['option_price_' + str(product_2_op_1.id)] = '25'
            product_2_op_2 = product_2.options.filter_by(
                option_name='L').first()
            self.product_2_edit['option_name_' + str(product_2_op_2.id)] = 'L'
            self.product_2_edit['option_price_' + str(product_2_op_2.id)] = '25'

    def test2_update_products(self):
        with self.client as c:
            response = c.post(url_for('auth.login'), data={
                'email': 'chair@conferency.com',
                'password': 'test'
            }, follow_redirects=True)

            self.assertTrue(
                response.status_code == 200, msg="Login failed.")
            current_user.set_conference_id(2)
            # update products
            response = c.post(url_for('conference.registration_products',
                                      conference_id=2),
                              data=self.product_1_edit,
                              follow_redirects=True)
            product_1 = Product.query.filter_by(name='Tour pass').first()
            self.assertTrue(
                product_1.price == 600.0 and product_1.currency == 'CNY',
                msg='update product 1')
            response = c.post(url_for('conference.registration_products',
                                      conference_id=2),
                              data=self.product_2_edit,
                              follow_redirects=True)
            product_2 = Product.query.filter_by(name='T shirt').first()
            product_2_op_1 = product_2.options.filter_by(
                option_name='L').first()
            product_2_op_2 = product_2.options.filter_by(
                option_name='M').first()
            self.assertTrue(
                (product_2_op_1 and product_2_op_1.option_price == 25.0) and
                (product_2_op_2 and product_2_op_2.option_price == 20.0),
                msg='update product 2')
