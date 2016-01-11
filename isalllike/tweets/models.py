from functools import reduce

from django.db import models
from django.conf import settings
from django.db import transaction

import ipdb
import nltk
from nltk.util import ngrams

# Create your models here.

from TwitterAPI import TwitterAPI

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
    def oldest_for_user(self, username):
        oldest_tweet = Tweet.objects.order_by('-twitter_id').last()
        if oldest_tweet:
            return oldest_tweet.twitter_id
        else:
            return None

    @classmethod
    def gather_for_user(self, username):
        while Tweet.gather_older_for_user(
                username,
                Tweet.oldest_for_user(username)
        ):
            pass

    @classmethod
    def gather_older_for_user(self, username, before_this_id=None):
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


class NGram(models.Model):
    token_one = models.CharField(max_length=255,)
    token_two = models.CharField(max_length=255, null=True)
    token_three = models.CharField(max_length=255, null=True)

    tag_one = models.CharField(max_length=255,)
    tag_two = models.CharField(max_length=255, null=True)
    tag_three = models.CharField(max_length=255, null=True)

    source = models.CharField(max_length=255,)

    def __str__(self):
        return (
            "<NGram {0.source}: ["
            "({0.token_one}, {0.tag_one}), "
            "({0.token_two}, {0.tag_two}), "
            "({0.token_three}, {0.tag_three})"
            "]>"
        ).format(self)

    @classmethod
    def _params_from_list(self, list_of_3_parsed_tokens, user):
        return {
            'token_one': list_of_3_parsed_tokens[0][0],
            'token_two': list_of_3_parsed_tokens[1][0],
            'token_three': list_of_3_parsed_tokens[2][0],
            'tag_one': list_of_3_parsed_tokens[0][1],
            'tag_two': list_of_3_parsed_tokens[1][1],
            'tag_three': list_of_3_parsed_tokens[2][1], 
            'source': user+'@twitter'
        }


    @classmethod
    def new_ngrams_from_twitter_sentences(self, parsed_sentences, username):
        with transaction.atomic():
            for ps in parsed_sentences:
                for ngram in ngrams(ps, 3):
                    NGram.objects.create(
                        **self._params_from_list(ngram, username)
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
