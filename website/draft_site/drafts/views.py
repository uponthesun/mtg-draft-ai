from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.


def index(request):
    return render(request, 'drafts/index.html', {})


def create_draft(request):
    pass


def draft(request, draft_id):
    pass
