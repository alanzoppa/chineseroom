from django.test import TestCase, TransactionTestCase
import vcr
from .models import Tweet

# Create your tests here.

class TwitterApiTest(TestCase):
    #def test_gather_for_user(self):
        #with vcr.use_cassette('tweets/vcr_cassettes/c_alan_zoppa_first_100.yml'):
            #Tweet.gather_for_user('c_alan_zoppa')

    def test_oldest_for_user(self):
        with vcr.use_cassette('tweets/vcr_cassettes/page_in_history.yml', record_mode='new_episodes'):
            Tweet.gather_for_user('c_alan_zoppa')
            Tweet.oldest_for_user('c_alan_zoppa')
