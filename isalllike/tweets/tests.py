from django.test import TestCase, TransactionTestCase
import vcr
from .models import Tweet


class TwitterApiTest(TransactionTestCase):
    def test_oldest_for_user(self):
        assert Tweet.oldest_for_user('c_alan_zoppa') == None
        Tweet.objects.create(
                    message="arbitrary",
                    user='c_alan_zoppa',
                    twitter_id='2'
        )
        Tweet.objects.create(
                    message="arbitrary",
                    user='c_alan_zoppa',
                    twitter_id='1'
        )
        assert Tweet.oldest_for_user('c_alan_zoppa') == '1'


    def test_gather_for_user(self):
        with vcr.use_cassette('tweets/vcr_cassettes/page_in_history.yml', record_mode='new_episodes'):
            Tweet.gather_for_user('c_alan_zoppa')
        assert Tweet.objects.count() == 315
