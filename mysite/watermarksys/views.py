from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render
from .models import *
def index(request):
    list=users.objects.all()
    context = {'latest_question_list': list}
    return render(request, 'watermarksys/index.html', context)
def login(request):
    try:
        getuser=users.objects.get(phone=request.POST['phone'])
        if(getuser.password==request.POST['password']):
            return render(request,'watermarksys/main.html')
    except:
        return render(request,'watermarksys/index.html')
def getregister(request):
    watermarks=watermark.objects.all()

    context = {'imagepath': watermarks}
    return render(request,'watermarksys/register.html',context)


# Create your views here.
