from django.shortcuts import render
from isalllike.tweets.models import NGram, NovelParagraph
import ipdb

# Create your views here.

def index(request):
    context = {
        'sources': [n.source for n in NGram.objects.all().distinct('source')],
    }


    if request.method == 'POST':
        #post_dictionary = copy(request.POST)
        sources = filter(lambda x: x.startswith('source-'), request.POST)
        sources = [(s[7:], int(request.POST[s])/100) for s in sources if request.POST[s] != '0']
        paragraph = NovelParagraph(*sources)
        paragraph.append_sentence()
        paragraph.append_sentence()
        paragraph.append_sentence()
        context['sentences'] = paragraph.human_readable_sentences()

    return render(
        request=request,
        template_name='tweets/index.html',
        context=context,
        )
