from django.test import TestCase, TransactionTestCase, SimpleTestCase
import vcr
from .models import Tweet, NGram, Parser

import ipdb


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

class ParserSimpleTest(SimpleTestCase):
    def test_merge_leading_chars(self):
        merged = Parser.merge_leading_chars([
            ('@', 'AAA'),
            ('herbert', 'CCC'),
            ('this', 'AAA'),
            ('is', 'AAA'),
            ('a', 'AAA'),
            ('#', 'AAA'),
            ('message', 'BBB'),
            ('for', 'AAA'),
            ('#', 'AAA'),
            ('you', 'BBB'),
        ], ('#', '@'))

        assert merged == [
            ('@herbert', '@+CCC'),
            ('this', 'AAA'),
            ('is', 'AAA'),
            ('a', 'AAA'),
            ('#message', '#+BBB'),
            ('for', 'AAA'),
            ('#you', '#+BBB'),
        ]

    def test_twitter_parse(self):
        test_string = '@herbert this is a #message for #you'
        output = Parser.twitter_transform_sentence(test_string)

        expected = [
            ('@herbert', '@+NN'),
            ('this', 'DT'),
            ('is', 'VBZ'),
            ('a', 'DT'),
            ('#message', '#+NN'),
            ('for', 'IN'),
            ('#you', '#+PRP')
        ]

        assert output == expected
        assert Parser.twitter_parse(test_string) == [expected]
