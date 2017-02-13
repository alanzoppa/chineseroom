from django.shortcuts import render, redirect
from isalllike.tweets.models import NGram, NovelParagraph, TwitterUser, Document, Tweet
import ipdb

def add_twitter_user(request):
    context = {}
    if request.method == "POST":
        Tweet.gather_history_for(request.POST['username'])
        return redirect('/')
    return render(
        request=request,
        template_name='tweets/add_twitter_user.html',
        context=context,
    )
 

def index(request):
    context = {}
    context['strategy'] = 'best'
    if request.method == 'POST':
        context.update(_get_sources(request.POST))
        paragraph = NovelParagraph(
            *_extract_probabilities(request.POST),
            strategy=request.POST['strategy']
        )
        context['sentences'] = _generate_markov_string(paragraph)
        context['strategy'] = request.POST['strategy']
    else:
        context.update(_get_sources())

    return render(
        request=request,
        template_name='tweets/index.html',
        context=context,
        )

def _extract_probabilities(data):
    prefix = 'source-'
    sources = filter(lambda x: x.startswith(prefix), data)
    return [
        (s[len(prefix):], int(data[s])/100)
        for s in sources if data[s] != '0'
    ]

def _get_sources(data={}):
    documents = Document.objects.all()
    twitter_users = TwitterUser.objects.all()
    for document in documents:
        key = 'source-document:'+document.name
        if key in data:
            document.ratio = data[key]
        else:
            document.ratio = 0
    for twitter_user in twitter_users:
        key = 'source-'+twitter_user.twitter_id+'@twitter'
        if key in data:
            twitter_user.ratio = data[key]
        else:
            twitter_user.ratio = 0
    return {
        'documents': documents,
        'twitter_users': twitter_users
    }


def _generate_markov_string(novel_paragraph):
    while len(novel_paragraph.human_readable_sentences()) < 120:
        novel_paragraph.append_sentence()
    return novel_paragraph.human_readable_sentences()
