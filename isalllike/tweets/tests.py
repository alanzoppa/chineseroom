from django.test import TestCase, TransactionTestCase
import vcr
from .models import Tweet

# Create your tests here.

class TwitterApiTest(TransactionTestCase):
    def test_gather_for_user(self):
        with vcr.use_cassette('tweets/vcr_cassettes/c_alan_zoppa_first_100.yml'):
            Tweet.gather_for_user('c_alan_zoppa')
