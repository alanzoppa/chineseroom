from django.shortcuts import render
from isalllike.tweets.models import NGram
import ipdb

# Create your views here.

def index(request):
    if request.method == 'POST':
        #post_dictionary = copy(request.POST)
        sources = filter(lambda x: x.startswith('source-'), request.POST)
        sources = [(s[7:], int(request.POST[s])) for s in sources]
        assert False

    context = {
        'sources': [n.source for n in NGram.objects.all().distinct('source')],
    }

    return render(
        request=request,
        template_name='tweets/index.html',
        context=context,
        )
