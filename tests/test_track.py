# -*- coding: utf-8 -*-
"""Test tracks."""
import unittest
import threading
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
# from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from app import create_app

timeout = 10


class TrackTestCase(unittest.TestCase):
    client = None

    base_url = 'http://127.0.0.1:5000'

    @classmethod
    def setUpClass(cls):
        # start Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--kiosk')
        try:
            # webdriver.Chrome(executable_path="chromedriver")
            cls.client = webdriver.Chrome(chrome_options=options)
        except Exception as e:
            print e.message
            pass

        # skip these tests if the browser could not be started
        if cls.client:
            # create the application
            cls.app = create_app('testing')
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # suppress logging to keep unittest output clean
            import logging
            logger = logging.getLogger('werkzeug')
            logger.setLevel("ERROR")

            # start the Flask server in a thread
            threading.Thread(target=cls.app.run).start()

            # give the server a second to ensure it is up
            time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # stop the flask server and the browser
            cls.client.get('http://127.0.0.1:5000/shutdown')
            cls.client.close()

            # remove application context
            cls.app_context.pop()

    def setUp(self):
        if not self.client:
            self.skipTest('Web browser not available')

    def tearDown(self):
        pass

    def get_element_present_by_id(self, element_id):
        return EC.presence_of_element_located((By.ID, element_id))

    def get_element_present_by_xpath(self, xpath):
        return EC.presence_of_element_located((By.XPATH, xpath))

    def get_element_visible_by_id(self, element_id):
        return EC.visibility_of_element_located((By.ID, element_id))

    def get_element_visible_by_xpath(self, xpath):
        return EC.visibility_of_element_located((By.XPATH, xpath))

    def test1_login(self):
        # go to login page
        self.client.get('http://127.0.0.1:5000/auth/login')
        self.assertTrue('Conferency | Login' == self.client.title)
        # login
        self.client.find_element_by_id('email').send_keys(
            'chair@conferency.com')
        self.client.find_element_by_id('password').send_keys('test')
        self.client.find_element_by_id('submit').click()
        try:
            # wait until dashboard loaded
            dashboard_element = self.get_element_present_by_id('dashboard')
            WebDriverWait(self.client, timeout).until(dashboard_element)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        self.assertTrue('Conferency | Dashboard' == self.client.title)

    def test2_add_track(self):
        self.client.find_element_by_id('conferenceManagement').click()
        try:
            # wait until tracks link showed
            tracks_element = self.get_element_visible_by_id('tracks')
            WebDriverWait(self.client, timeout).until(tracks_element)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        self.client.find_element_by_id('tracks').click()
        # add new first track
        self.client.find_element_by_id('new_track').send_keys('test_track_1')
        self.client.find_element_by_id('add_new_track').click()
        try:
            # wait until tracks link showed
            track_1_element = self.get_element_present_by_xpath(
                '//span[@class=\'track_name\']' +
                '[contains(text(), \'test_track_1\')]')
            WebDriverWait(self.client, timeout).until(track_1_element)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        # add new second track
        self.client.find_element_by_id('new_track').send_keys('test_track_2')
        self.client.find_element_by_id('add_new_track').click()
        try:
            # wait until tracks link showed
            track_2_element = self.get_element_present_by_xpath(
                '//span[@class=\'track_name\']' +
                '[contains(text(), \'test_track_2\')]')
            WebDriverWait(self.client, timeout).until(track_2_element)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        # add new third track
        self.client.find_element_by_id('new_track').send_keys('test_track_3')
        self.client.find_element_by_id('add_new_track').click()
        try:
            # wait until tracks link showed
            track_3_element = self.get_element_present_by_xpath(
                '//span[@class=\'track_name\']' +
                '[contains(text(), \'test_track_3\')]')
            WebDriverWait(self.client, timeout).until(track_3_element)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)

    def test3_delete_track(self):
        delete_button = self.client.find_element_by_xpath(
            '//span[@class=\'track_name\']' +
            '[contains(text(), \'test_track_3\')]' +
            '/preceding-sibling::' +
            'span[@class=\'pull-right dd-nodrag margin-buttom-10\']' +
            '/button[@class=\'btn btn-danger btn-circle delete_track\']')
        delete_button.click()
        try:
            # confirm warning sweet alert shows
            sweetAlert_div = self.get_element_present_by_xpath(
                '//div[@class=\'sweet-alert showSweetAlert visible\']')
            sweetAlert_div = WebDriverWait(
                self.client, timeout).until(sweetAlert_div)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        sweetAlert_div.find_element_by_xpath(
            '//button[@class=\'confirm\']' +
            '[contains(text(), \'Yes, get it done!\')]').click()
        try:
            # confirm success sweet alert shows
            sweetAlert_success_div = self.get_element_present_by_xpath(
                '//div[@class=\'sweet-alert showSweetAlert visible\']' +
                '/div[@class=\'sa-icon sa-success animate\']')
            WebDriverWait(self.client, timeout).until(sweetAlert_success_div)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        try:
            self.client.find_element_by_xpath(
                '//span[@class=\'track_name\']' +
                '[contains(text(), \'test_track_3\')]')
            self.assertTrue(False)
        except NoSuchElementException:
            pass

    def test4_edit_track(self):
        # make track_2 a sub track of track 1
        # cannot be done
        # update track name
        self.client.get('http://127.0.0.1:5000/conference/2/tracks')
        edit_button = self.client.find_element_by_xpath(
            '//span[@class=\'track_name\']' +
            '[contains(text(), \'test_track_2\')]' +
            '/preceding-sibling::' +
            'span[@class=\'pull-right dd-nodrag margin-buttom-10\']' +
            '/button[@class=\'btn btn-warning btn-circle edit_track\']')
        edit_button.click()
        try:
            # confirm input shows
            edit_input = self.get_element_present_by_xpath(
                '//input[@class=\'dd-nodrag\']')
            edit_input = WebDriverWait(
                self.client, timeout).until(edit_input)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
        edit_input.send_keys('_edited')
        confirm_button = self.client.find_element_by_xpath(
            '//input[@class=\'dd-nodrag\']' +
            '/preceding-sibling::' +
            'span[@class=\'pull-right dd-nodrag margin-buttom-10\']' +
            '/button[@class=\'btn btn-info btn-circle track_edit_confirm\']')
        confirm_button.click()
        try:
            # confirm warning sweet alert shows
            test_track_2_edit = self.get_element_present_by_xpath(
                '//span[@class=\'track_name\']' +
                '[contains(text(), \'test_track_2_edit\')]')
            edit_input = WebDriverWait(
                self.client, timeout).until(test_track_2_edit)
        except TimeoutException:
            print 'Timed out waiting for page to load'
            self.assertTrue(False)
