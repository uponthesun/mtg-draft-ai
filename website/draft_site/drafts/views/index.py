from django.shortcuts import render
from ..constants import CUBES


# /
def index(request):
    return render(request, 'drafts/index.html', {'cubes': CUBES})
