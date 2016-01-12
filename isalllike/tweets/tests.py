from django.test import TestCase, TransactionTestCase, SimpleTestCase
import vcr
from .models import Tweet, NGram, Parser, NovelParagraph, Document
from .models import InvalidSourceException

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
        NGram.new_ngrams_from_parsed_sentences( [self.twitter_sentence],'c_alan_zoppa@twitter')
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
        NGram.new_ngrams_from_parsed_sentences(sentence, 'fake_user@twitter')
        sentence = Parser.twitter_parse(
            "As if one could kill time without injuring eternity."
        )
        NGram.new_ngrams_from_parsed_sentences(sentence, 'hd_thoreau@twitter')

    def test_start_sentence_marker(self):
        first = NGram.objects.get(token_one='The')
        assert first.sentence_starter

    def test_end_sentence_marker(self):
        last = NGram.objects.get(token_three='#blessed')
        assert last.sentence_terminator

    def test_basics(self):
        nov = NovelParagraph(('fake_user@twitter', 1))
        nov.append_sentence()
        assert nov.human_readable_sentences() == (
            "The quick brown fox jumped over a lazy dog #blessed."
        )

    def test_initialize_with_bad_data(self):
        try:
            nov = NovelParagraph(('invalid@twitter', 1))
            passed = False
        except InvalidSourceException:
            passed = True
        assert passed
            

    #def test_compound(self):
        #nov = NovelParagraph(('fake_user@twitter', .5), ('hd_thoreau@twitter', .5))
        #nov.append_sentence()
        #nov.append_sentence()
        #print(nov.human_readable_sentences())


class DocumentTests(TransactionTestCase):
    def setUp(self):
        self.test_document = Document.objects.create(
            name='Psalm 63',
            text=(
                "But those that seek my soul, to destroy it, shall go into "
                "the lower parts of the earth. They shall fall by the sword: "
                "they shall be a portion for foxes."
            )
        )

    def test_document_parse(self):
        parsed = Parser.document_parse(self.test_document.text)
        assert parsed == [
            [
                ('But', 'CC'), ('those', 'DT'), ('that', 'WDT'),
                ('seek', 'VBP'), ('my', 'PRP$'), ('soul', 'NN'), (',', ','),
                ('to', 'TO'), ('destroy', 'VB'), ('it', 'PRP'), (',', ','),
                ('shall', 'MD'), ('go', 'VB'), ('into', 'IN'), ('the', 'DT'),
                ('lower', 'JJR'), ('parts', 'NNS'), ('of', 'IN'),
                ('the', 'DT'), ('earth', 'NN'), ('.', '.')
            ],
            [
                ('They', 'PRP'), ('shall', 'MD'), ('fall', 'VB'), ('by', 'IN'),
                ('the', 'DT'), ('sword', 'NN'), (':', ':'), ('they', 'PRP'),
                ('shall', 'MD'), ('be', 'VB'), ('a', 'DT'), ('portion', 'NN'),
                ('for', 'IN'), ('foxes', 'NNS'), ('.', '.')
            ]
        ]

    def test_rebuild_ngrams_signal(self):
        Document.objects.create(
            name='arbitrary',
            text="This is just to test the signal."
        )
        assert NGram.objects.filter(source='document:arbitrary').count() == 6

    def test_rebuild_ngrams(self):
        source_name = 'document:'+self.test_document.name
        NGram.objects.filter(source=source_name).delete()
        self.test_document.rebuild_ngrams()
        assert NGram.objects.filter(source=source_name).count() == 32


class SentencePostprocessing(TransactionTestCase):

    def setUp(self):
        example = (
            "@joe has an example! Take a look; it's at "
            "http://www.example.com. Hurry, or you'll miss it."
        )

        sentence = Parser.twitter_parse(example)
        NGram.new_ngrams_from_parsed_sentences(sentence, 'fake_user@twitter')

    def test_humanize_sentence(self):
        nov = NovelParagraph(('fake_user@twitter', 1))
        for i in range(0,100):
            nov.append_sentence()
        humanized = nov.human_readable_sentences()
        for i in [
            "@joe has an example!",
            "Take a look; it's at http://www.example.com.",
            "Hurry, or you'll miss it."
        ]:
            assert i in humanized
