from django.db import models
from django.conf import settings
from django.db import transaction

import ipdb

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
        while Tweet.gather_older_for_user(username, Tweet.oldest_for_user(username)):
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
