from django.shortcuts import render
from isalllike.tweets.models import NGram, NovelParagraph, TwitterUser, Document
import ipdb

# Create your views here.

def index(request):
    context = {
        'documents': Document.objects.all(),
        'twitter_users': TwitterUser.objects.all()
    }
    if request.method == 'POST':
        paragraph = NovelParagraph( *_extract_probabilities(request.POST) )
        context['sentences'] = _generate_markov_string(paragraph)

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

def _generate_markov_string(novel_paragraph):
    novel_paragraph.append_sentence()
    novel_paragraph.append_sentence()
    novel_paragraph.append_sentence()
    return novel_paragraph.human_readable_sentences()
