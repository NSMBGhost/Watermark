from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render
from .models import *
def index(request):
    list=users.objects.all()
    context = {'latest_question_list': list}
    return render(request, 'watermarksys/index.html', context)
# Create your views here.
