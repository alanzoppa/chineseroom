from django.contrib import admin
from .models import Document, TwitterUser


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    ordering = ('name',)
    search_fields = ['name',] 

@admin.register(TwitterUser)
class TwitterUserAdmin(admin.ModelAdmin):
    list_display = ('twitter_id',)
    pass
