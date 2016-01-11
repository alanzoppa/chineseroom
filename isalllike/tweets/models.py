from functools import reduce

from multiprocessing import Pool
from random import shuffle

from django.db import models
from django.conf import settings
from django.db import transaction

import ipdb
import nltk
from nltk.util import ngrams
from nltk.probability import DictionaryProbDist


from TwitterAPI import TwitterAPI

NO_LEADING_SPACE_TOKENS = [
    '.', ',', '!', '?', ':', ';', '"', "'", "n't", "'d", "'s", ')',
    "'ll", "'m", "'ve", "'re",
]

NO_TRAILING_SPACE_TOKENS = ['(', '@', ]



api = TwitterAPI(**settings.TWITTER_AUTHENTICATION)

class Tweet(models.Model):
    message = models.TextField(blank=True, null=True)
    user = models.CharField(max_length=255,)
    twitter_id = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.user + ': ' + self.message

    class Meta:
        ordering = ['-twitter_id']


    @classmethod
    def _oldest_for_user(self, username):
        oldest_tweet = Tweet.objects.order_by('-twitter_id').last()
        if oldest_tweet:
            return oldest_tweet.twitter_id
        else:
            return None

    @classmethod
    def _gather_for_user(self, username):
        while Tweet._gather_older_for_user(
                username,
                Tweet._oldest_for_user(username)
        ):
            pass

    @classmethod
    def _gather_older_for_user(self, username, before_this_id=None):
        params = {'count': 100, 'include_rts': False,}
        if before_this_id:
            params['max_id'] = str(before_this_id)
        request = api.request('statuses/user_timeline', params)
        tweets = [t for t in request]

        try:
            Tweet.objects.get(twitter_id=tweets[-1]['id_str'])
            return None
        except Tweet.DoesNotExist:
            pass

        with transaction.atomic():
            for t in tweets:
                Tweet.objects.get_or_create(
                    message=t['text'],
                    user=username,
                    twitter_id=t['id']
                )
        return True

    @classmethod
    def gather_history_for(self, username):
        Tweet._gather_older_for_user(username)

        pool = Pool(processes=4)
        lists_of_messages = pool.map(
            Parser.twitter_parse,
            [sentence.message
             for sentence in Tweet.objects.filter(user=username)
             ]
        )

        for l in lists_of_messages:
            NGram.new_ngrams_from_twitter_sentences(
                l, username
            )


class NGram(models.Model):
    token_one = models.CharField(max_length=255,)
    token_two = models.CharField(max_length=255, null=True)
    token_three = models.CharField(max_length=255, null=True)

    tag_one = models.CharField(max_length=255,)
    tag_two = models.CharField(max_length=255, null=True)
    tag_three = models.CharField(max_length=255, null=True)

    source = models.CharField(max_length=255,)

    sentence_starter = models.BooleanField(default=False)
    sentence_terminator = models.BooleanField(default=False)

    def __str__(self):
        return (
            "<NGram {0.source}: ["
            "({0.token_one}, {0.tag_one}), "
            "({0.token_two}, {0.tag_two}), "
            "({0.token_three}, {0.tag_three})"
            "]>"
        ).format(self)

    @classmethod
    def _params_from_list(self, *args, **kwargs):
        three_parsed_tokens = args[0]
        base = {
            'token_one': three_parsed_tokens[0][0],
            'token_two': three_parsed_tokens[1][0],
            'token_three': three_parsed_tokens[2][0],
            'tag_one': three_parsed_tokens[0][1],
            'tag_two': three_parsed_tokens[1][1],
            'tag_three': three_parsed_tokens[2][1], 
        }
        base.update(kwargs)
        return base


    @classmethod
    def new_ngrams_from_twitter_sentences(self, parsed_sentences, username):
        with transaction.atomic():
            for ps in parsed_sentences:
                sentence_ngrams = [n for n in ngrams(ps,3)]
                final_ngram_index = len(sentence_ngrams)-1
                for i, ngram in enumerate(sentence_ngrams):
                    NGram.objects.create(
                        **self._params_from_list(
                            ngram,
                            source=username+'@twitter',
                            sentence_starter=(i == 0),
                            sentence_terminator=(i == final_ngram_index)
                            )
                    )


class Parser:
    @classmethod 
    def _merge_leading_chars(self, text, characters): 
        def handle_chars(already, new):
            if already == []:
                return [new]
            if already[-1][0] in characters:
                char = already[-1][0]
                munged = (
                    "{old}{new}".format(old=char, new=new[0]),
                    "{old}+{pos}".format(old=char, pos=new[1])
                )
                already[-1] = munged
            else:
                already.append(new)
            return already 
        return reduce(handle_chars, text, [])

    # Accepts
    # [ ('@', 'whatever'), ('word', 'pos_tag'), ]
    #
    # Returns
    # [ ('@word', '@+pos_tag'), ]
    @classmethod
    def _twitter_transform_sentence(self, sentence):
        return Parser._merge_leading_chars(
            nltk.pos_tag(
                nltk.word_tokenize(sentence)
            ),
            ('@', '#')
        )

    # Accepts
    # "@lorem ipsum. Dolor sit amet."
    #
    # Returns
    # [ ('@word', '@+pos_tag'), ... ]
    @classmethod
    def twitter_parse(self, text):
        return [
            Parser._twitter_transform_sentence(sentence)
            for sentence in nltk.sent_tokenize(text)
        ]


class NovelParagraph:
    def __init__(self, *args):
        self.events = []
        self.sentences = []
        self.source_probability = {}
        self.querysets = {}
        self.sources = []
        for source, probability in args:
            self.source_probability[source] = probability
            self.querysets[source] = NGram.objects.filter(source=source)
            self.sources.append(source)
        self.source_probability = DictionaryProbDist(self.source_probability)

    def pick_queryset(self):
        return self.querysets[self.source_probability.generate()]

    def append_sentence(self):
        self.current_sentence = []
        starter = self.pick_queryset().filter(sentence_starter=True).order_by('?').first()
        self.current_sentence.append(starter.token_one)
        self.current_sentence.append(starter.token_two)
        self.current_sentence.append(starter.token_three)
        while self.current_sentence[-1] not in ['.', '!', '?']:
            new_word = self.new_word()
            self.current_sentence.append(new_word)
        self.sentences.append(self.current_sentence)

    def _get_others(self, original):
        sources = self.sources.copy()
        sources.remove(original)
        return [NGram.objects.filter(source=source) for source in sources]

    def new_word(self):
        queryset = self.pick_queryset()
        ordered_querysets = [queryset]

        if len(self.sources) > 1:
            ordered_querysets = ordered_querysets + self._get_others(queryset.first().source)

        for qs in ordered_querysets:
            new_word = self.new_word_from_queryset(qs)
            if new_word:
                return new_word
        return '.'

    def new_word_from_queryset(self, queryset):
        nxt = queryset.filter(
            token_one__iexact=self.current_sentence[-2],
            token_two__iexact=self.current_sentence[-1],
        ).order_by('?').first()
        if nxt:
            return nxt.token_three
        else:
            return None

    def human_readable_sentences(self):
        final_output = []
        for sentence in self.sentences:
            output = []
            for i, token in enumerate(sentence):
                if \
                        i != 0 and \
                        sentence[i-1] not in NO_TRAILING_SPACE_TOKENS and \
                        sentence[i] not in NO_LEADING_SPACE_TOKENS:
                    output.append(' ')
                output.append(token)
            final_output.append(''.join(output))
        return ' '.join(final_output)
