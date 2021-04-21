from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import *
import os
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
def getregister(request):
    watermarks=watermark.objects.all()
    context = {'imagepath': watermarks}
    return render(request,'watermarksys/register.html',context)
def getfileload(request):
    if login_check(request)==1:
        return render(request,'watermarksys/watermark_create.html')
@csrf_exempt
def embed(request):
    if login_check(request)==1:
        if request.method == 'POST':
            file_obj = request.FILES.get('file')
            baseDir = os.path.dirname(os.path.abspath(__name__))  # 获取运行路径
            jpgdir = os.path.join(baseDir, 'watermarksys','static','watermarksys','images',str(file_obj.name))  # 加上media路径
            print(jpgdir)
            f = open(jpgdir, 'wb')
            print(file_obj, type(file_obj))
            for chunk in file_obj.chunks():
                f.write(chunk)
            f.close()
            print('11111')
            return HttpResponse('OK')
# Create your views here.
