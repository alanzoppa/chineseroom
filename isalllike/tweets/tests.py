from django.test import TestCase, TransactionTestCase, SimpleTestCase
import vcr
from .models import Tweet, NGram, Parser, NovelParagraph

import ipdb


class TwitterApiTest(TransactionTestCase):
    def test_oldest_for_user(self):
        assert Tweet._oldest_for_user('c_alan_zoppa') == None
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
        assert Tweet._oldest_for_user('c_alan_zoppa') == '1'


    def test_gather_for_user(self):
        with vcr.use_cassette(
                'tweets/vcr_cassettes/page_in_history.yml',
                record_mode='new_episodes'
        ):
            Tweet._gather_for_user('c_alan_zoppa')
        assert Tweet.objects.count() == 315

class ParserSimpleTest(SimpleTestCase):
    def test_merge_leading_chars(self):
        merged = Parser._merge_leading_chars([
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
        output = Parser._twitter_transform_sentence(test_string)

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


class TwitterNGramTest(TransactionTestCase):

    def setUp(self):
        self.twitter_sentence = [
            ('@herbert', '@+NN'),
            ('this', 'DT'),
            ('is', 'VBZ'),
            ('a', 'DT'),
            ('#message', '#+NN'),
            ('for', 'IN'),
            ('#you', '#+PRP')
        ]

    def test_params_from_list(self):
        params = NGram._params_from_list(
            [
                ('@herbert', '@+NN'),
                ('this', 'DT'),
                ('is', 'VBZ'),
            ],
            source='c_alan_zoppa@twitter',
            sentence_starter=True,
            sentence_terminator=False
        )

        assert params == {
            'tag_two': 'DT',
            'sentence_starter': True,
            'token_two': 'this',
            'tag_one': '@+NN',
            'token_one': '@herbert',
            'tag_three': 'VBZ',
            'source': 'c_alan_zoppa@twitter',
            'token_three': 'is',
            'sentence_terminator': False
        }

    def test_ngramify_twitter_sentence(self):
        NGram.new_ngrams_from_twitter_sentences( [self.twitter_sentence],'c_alan_zoppa')
        first = NGram.objects.first()
        assert NGram.objects.count() == 5
        assert first.token_one == '@herbert'
        assert first.token_two == 'this'
        assert first.token_three == 'is'
        assert first.tag_one == '@+NN'
        assert first.tag_two == 'DT'
        assert first.tag_three == 'VBZ'
        assert first.source == 'c_alan_zoppa@twitter'


class EndToEndGatherTest(TransactionTestCase):
    def test_gather_history_for(self):
        with vcr.use_cassette(
                'tweets/vcr_cassettes/page_in_history.yml',
                record_mode='new_episodes'
        ):
            Tweet.gather_history_for('c_alan_zoppa') 
        assert NGram.objects.count() == 1152


class NovelParagraphTests(TransactionTestCase):
    def setUp(self):
        sentence = Parser.twitter_parse(
            "The quick brown fox jumped over a lazy dog #blessed"
        )
        NGram.new_ngrams_from_twitter_sentences(sentence, 'fake_user')

    def test_end_sentence_marker(self):
        last = NGram.objects.get(token_three='#blessed')
        assert last.sentence_terminator

    def test_basics(self):
        n=NovelParagraph([NGram.objects.all()])
        n.append_sentence()
        assert n.human_readable_sentences() == (
            "The quick brown fox jumped over a lazy dog #blessed."
        )
