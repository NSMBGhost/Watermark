from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import *
import datetime
import json
import os
def queryuser(phonea):
    try:
        usera=users.objects.get(phone=phonea)
        return 1
    except:
        return 0
def set_default(obj):
     if isinstance(obj, set):
         return list(obj)
     raise TypeError
def index(request):
    list=users.objects.all()
    context = {'latest_question_list': list}
    return render(request, 'watermarksys/index.html', context)
def login_check(request):
    if request.session['islogin']==1:
        return 1
    else:
        return render(request,'watermarksys/index.html')
def login(request):
    try:
        getuser=users.objects.get(phone=request.POST['phone'])
        if(getuser.password==request.POST['password']):
            #request.session.set_expiry(2)
            request.session['islogin']=1
            request.session['phone']=getuser.phone
            return render(request,'watermarksys/main.html')
    except:
        return render(request,'watermarksys/index.html')
def loginout(request):
    request.session['islogin']=0
    return HttpResponseRedirect('/watermarksys')
def getregister(request):
    return render(request,'watermarksys/register.html')
def gethistory(request):
    if login_check(request)==1:
        phoneunm=request.session['phone']
        return render(request, 'watermarksys/history.html')
    else:
        return HttpResponseRedirect('/')
def getaccount(request):
    if login_check(request) == 1:
        return render(request, 'watermarksys/account.html')
    else:
        return HttpResponseRedirect('/')
def getprofile(request):
    if login_check(request) == 1:
        return render(request, 'watermarksys/profile.html')
    else:
        return HttpResponseRedirect('/')
def getindex(request):
    if login_check(request) == 1:
        return render(request, 'watermarksys/main.html')
    else:
        return HttpResponseRedirect('/')
@csrf_exempt
def register(request):
    phonevalue = request.POST['phonevalue']
    passwordvalue = request.POST['passwordvalue']
    if queryuser(phonevalue):
        backdict = {'code': 0}
        return JsonResponse(backdict)
    else:
        insert = users(phone=phonevalue, password=passwordvalue)
        insert.save()
        backdict = {'code': 1}
        return JsonResponse(backdict)
@csrf_exempt
def embed(request):
    if login_check(request)==1:
        if request.method == 'POST':
            phonenum=request.session['phone']
            file_obj = request.FILES.get('file1')
            file_obj2 = request.FILES.get('file2')
            filesname = str(file_obj.name)[-10:]
            baseDir = os.path.dirname(os.path.abspath(__name__))  # 获取运行路径
            wjdir=os.path.join(baseDir, 'watermarksys','static','watermarksys','images',phonenum)
            if not os.path.exists(wjdir):
                os.makedirs(wjdir)
            jpgdir = os.path.join(baseDir, 'watermarksys','static','watermarksys','images',phonenum,filesname)  # 加上media路径
            print(jpgdir)
            now_time = datetime.datetime.now()
            time1_str = datetime.datetime.strftime(now_time, '%Y-%m-%d %H:%M:%S')
            f = open(jpgdir, 'wb')
            print(file_obj, type(file_obj))
            for chunk in file_obj.chunks():
                f.write(chunk)
            f.close()
            insertwater=watermark(phone=phonenum,upload_time=time1_str,syspath=str(os.path.join('static','watermarksys','images',phonenum,filesname)),filename=filesname)
            insertwater.save()
            return HttpResponse('OK')
# Create your views here.
