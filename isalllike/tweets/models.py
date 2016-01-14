from functools import reduce
import re

from multiprocessing import Pool
from random import shuffle

from django.db import models
from django.conf import settings
from django.db import transaction
from django.dispatch import receiver
from django.db.models.signals import post_save

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

UNUSABLE_TOKENS = ['``', '"']

REGEX_REPLACEMENTS = [
    (re.compile(r'(https?:) '), '\\1'),
]

api = TwitterAPI(**settings.TWITTER_AUTHENTICATION)


def reconcile_old_style_source(source):
    if source.startswith('document'):
        document_title = source.split(':')[-1]
        return {'document_id': Document.objects.get(name=document_title)}
    elif source.endswith('@twitter'):
        twitter_username = source.split('@')
        twitter_user, created = TwitterUser.objects.get_or_create(twitter_id=twitter_username)
        return {'twitter_user_id': twitter_user.id}




class TwitterUser(models.Model):
    twitter_id = models.CharField(max_length=255, unique=True)

class Tweet(models.Model):
    message = models.TextField(blank=True, null=True)
    user = models.CharField(max_length=255,)
    twitter_id = models.CharField(max_length=255, unique=True)
    twitter_user = models.ForeignKey('TwitterUser', null=True)

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
        params = {'count': 100, 'include_rts': False, 'screen_name': username}
        if before_this_id:
            params['max_id'] = str(before_this_id)
        request = api.request('statuses/user_timeline', params)
        tweets = [t for t in request]

        try:
            Tweet.objects.get(twitter_id=tweets[-1]['id_str'])
            return None
        except Tweet.DoesNotExist:
            pass

        twitter_user, created = TwitterUser.objects.get_or_create(
            twitter_id = username
        )

        with transaction.atomic():
            for t in tweets:
                Tweet.objects.get_or_create(
                    message=t['text'],
                    user=username,
                    twitter_user = twitter_user,
                    twitter_id=t['id']
                )
        return True

    @classmethod
    def gather_history_for(self, username):
        NGram.objects.filter(twitter_user__twitter_id=username).delete()
        Tweet._gather_older_for_user(username)

        pool = Pool(processes=4)
        lists_of_messages = pool.map(
            Parser.twitter_parse,
            [sentence.message
             for sentence in Tweet.objects.filter(user=username)
             ]
        )

        for l in lists_of_messages:
            NGram.new_ngrams_from_parsed_sentences(
                l, username+'@twitter'
            )


class NGram(models.Model):
    token_one = models.CharField(max_length=255,)
    token_two = models.CharField(max_length=255, null=True)
    token_three = models.CharField(max_length=255, null=True)

    tag_one = models.CharField(max_length=255,)
    tag_two = models.CharField(max_length=255, null=True)
    tag_three = models.CharField(max_length=255, null=True)

    document = models.ForeignKey('Document', null=True)
    twitter_user = models.ForeignKey('TwitterUser', null=True)

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

        if kwargs['source'].startswith('document'):
            document_title = kwargs['source'].split(':')[-1]
            base['document_id'] = Document.objects.get(name=document_title).id
        elif kwargs['source'].endswith('@twitter'):
            twitter_username = kwargs['source'].split('@')
            twitter_user, created = TwitterUser.objects.get_or_create(twitter_id=twitter_username)
            base['twitter_user_id'] = twitter_user.id

        del kwargs['source']

        base.update(kwargs)
        return base


    @classmethod
    def new_ngrams_from_parsed_sentences(self, parsed_sentences, source):
        with transaction.atomic():
            for ps in parsed_sentences:
                sentence_ngrams = [n for n in ngrams(ps,3)]
                final_ngram_index = len(sentence_ngrams)-1
                for i, ngram in enumerate(sentence_ngrams):
                    ngram=NGram.objects.create(
                        **self._params_from_list(
                            ngram,
                            source=source,
                            sentence_starter=(i == 0),
                            sentence_terminator=(i == final_ngram_index)
                            )
                    )


class Document(models.Model):
    name = models.CharField(max_length=255,)
    text = models.TextField()

    def rebuild_ngrams(self):
        source_name = 'document:'+self.name
        NGram.objects.filter(document=self).delete()
        NGram.new_ngrams_from_parsed_sentences(
            Parser.document_parse(self.text),
            source_name
        )

@receiver(post_save, sender=Document)
def generate_document_ngrams(sender, **kwargs):
    kwargs['instance'].rebuild_ngrams() 


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
            Parser.pos_tag_sentence(sentence),
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


    @classmethod
    def pos_tag_sentence(self, sentence):
        return nltk.pos_tag(nltk.word_tokenize(sentence))

    @classmethod
    def document_parse(self, text):
        return Pool(processes=4).map(
            Parser.pos_tag_sentence,
            nltk.sent_tokenize(text)
        )


class InvalidSourceException(Exception):
    pass


class NovelParagraph:
    def __init__(self, *args):
        self.events = []
        self.sentences = []
        self.source_probability = {}
        self.querysets = {}
        self.sources = []
        for source, probability in args:
            self.source_probability[source] = probability
            #self.querysets[source] = NGram.objects.filter(source=source)
            self.querysets[source] = NGram.objects.filter(**reconcile_old_style_source(source))
            self.sources.append(source)
            if self.querysets[source].count() == 0:
                raise InvalidSourceException("No NGrams with this source")
        self.source_probability = DictionaryProbDist(self.source_probability)

    def pick_queryset(self):
        return self.querysets[self.source_probability.generate()]

    def append_sentence(self):
        self.current_sentence = []
        starter = self.pick_queryset().filter(sentence_starter=True).order_by('?').first()
        self.current_sentence.append((starter.token_one, starter.tag_one))
        self.current_sentence.append((starter.token_two, starter.tag_two))
        self.current_sentence.append((starter.token_three, starter.tag_three))
        while self.current_sentence[-1][0] not in ['.', '!', '?']:
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
            token_one__iexact=self.current_sentence[-2][0],
            token_two__iexact=self.current_sentence[-1][0],
        ).order_by('?').first()
        if nxt:
            return (nxt.token_three, nxt.tag_three)
        else:
            return None

    @classmethod
    def _needs_space(self, token, previous_token, index):
        if index == 0:
            return False
        if previous_token in NO_TRAILING_SPACE_TOKENS:
            return False
        if token in NO_LEADING_SPACE_TOKENS:
            return False
        return True

    #@classmethod
    #def _reckon_quotations(self, sentences):
        #for i, sentence in enumerate(sentences):
            #if i == 0:
                #continue
            #if sentence[0] == sentence[0].lower():
                #senvk

    
    @classmethod
    def _join_and_postprocess_sentences(self, sentences):
        sentences = [''.join(sentence) for sentence in sentences]
        text = ' '.join(sentences)
        for pattern, replacement in REGEX_REPLACEMENTS:
            text = re.sub(pattern, replacement, text) 
        return text 
    
    @classmethod
    def _usable_token(self, token):
        return token not in UNUSABLE_TOKENS

    def human_readable_sentences(self):
        final_output = []
        for sent in self.sentences:
            output = []
            for i, token in enumerate(sent):
                if NovelParagraph._usable_token(token[0]):
                    if NovelParagraph._needs_space(token[0], sent[i-1][0], i):
                        output.append(' ')
                    output.append(token[0])
            final_output.append(output)
        return NovelParagraph._join_and_postprocess_sentences(final_output)
