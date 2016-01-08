from django.db import models
from django.conf import settings

# Create your models here.

from TwitterAPI import TwitterAPI

api = TwitterAPI(**settings.TWITTER_AUTHENTICATION)

class Tweet(models.Model):
    message = models.TextField(blank=True, null=True)
    user = models.CharField(max_length=255,)

    @classmethod
    def gather_for_user(self, username):
        return api.request('statuses/user_timeline', {'count': 100})
