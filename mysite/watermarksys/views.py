from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseRedirect

from django.http import FileResponse
from django.shortcuts import render,reverse
from django.views.decorators.csrf import csrf_exempt
from blind_watermark import WaterMark
from .models import *
import datetime
import json
import shutil
import cv2
import qrcode
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
        else:
            return render(request, 'watermarksys/index.html')
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
        getwatermark=watermark.objects.filter(phone=phoneunm)
        context={'getwatermark':getwatermark}
        return render(request, 'watermarksys/history.html',context)
    else:
        return HttpResponseRedirect("/watermarksys")
def getaccount(request):
    if login_check(request) == 1:
        return render(request, 'watermarksys/account.html')
    else:
        return HttpResponseRedirect('/')
def getprofile(request):
    if login_check(request) == 1:
        phoneunm = request.session['phone']
        getuserinformation=userinformation.objects.get(phone=phoneunm)
        context={'company':getuserinformation.company,
                 'address':str(getuserinformation.address).rstrip(),
                 'money':str(getuserinformation.money).rstrip(),
                 'phone':phoneunm}
        return render(request, 'watermarksys/profile.html',context)
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
        insert2=userinformation(phone=phonevalue,company="",address="",money=1)
        insert2.save()
        insert.save()
        backdict = {'code': 1}
        return JsonResponse(backdict)
@csrf_exempt
def embed(request):
    if login_check(request)==1:
        if request.method == 'POST':
            phonenum=request.session['phone']
            getuserinformation=userinformation.objects.get(phone=phonenum)
            if(getuserinformation.money<1):
                redic={'code':2}
                return JsonResponse(redic)
            file_obj = request.FILES.get('file1')
            embstr = request.POST.get('inputs')
            qr=qrcode.make(embstr)
            bwm1 = WaterMark(password_wm=1, password_img=1)
            filesname = str(file_obj.name)[-10:]
            filenamelist=filesname.split('.')
            filesname=filenamelist[0]+'.png'
            baseDir = os.path.dirname(os.path.abspath(__name__))  # 获取运行路径
            temdir=os.path.join(baseDir, 'watermarksys','static','watermarksys','images',phonenum,'temp')
            if os.path.exists(temdir):
                shutil.rmtree(temdir)
            os.makedirs(temdir)
            temdir_pic=os.path.join(temdir,filesname)
            temdir_qr=os.path.join(temdir,'qr.png')
            f=open(temdir_pic,'wb')
            for chunk in file_obj.chunks():
                f.write(chunk)
            with open(temdir_qr, 'wb') as f:
                qr.save(f)
            qr = cv2.imread(temdir_qr, 1)
            qr2 = cv2.resize(qr, (64, 64))
            cv2.imwrite(os.path.join(temdir,'qr2.png'), qr2)
            bwm1 = WaterMark(password_wm=1, password_img=1,d1=15,d2=1)
            bwm1.read_img(temdir_pic)
            bwm1.read_wm(os.path.join(temdir,'qr2.png'))
            wjdir=os.path.join(baseDir, 'watermarksys','static','watermarksys','images',phonenum)
            if not os.path.exists(wjdir):
                os.makedirs(wjdir)
            jpgdir = os.path.join(baseDir, 'watermarksys','static','watermarksys','images',phonenum,filesname)  # 加上media路径
            now_time = datetime.datetime.now()
            time1_str = datetime.datetime.strftime(now_time, '%Y-%m-%d %H:%M:%S')
            try:
                bwm1.embed(jpgdir)
                insertwater=watermark(phone=phonenum,upload_time=time1_str,syspath=str(os.path.join('static','watermarksys','images',phonenum,filesname)),filename=filesname)
                insertwater.save()
                money=getuserinformation.money
                money-=1
                getuserinformation.money=money
                getuserinformation.save()
                redic={'code':1}
                return JsonResponse(redic)
            except:
                redic = {'code': 0}
                return JsonResponse(redic)
    else:
        return HttpResponseRedirect("/watermarksys")
@csrf_exempt
def updateprofile(request):
    if login_check(request) == 1:
        newcompany=request.POST['company']
        newaddress=request.POST['address']
        phonenum=request.session['phone']
        updatepro=userinformation.objects.get(phone=phonenum)
        updatepro.company=newcompany
        updatepro.address=newaddress
        updatepro.save()
        #getuserinformation = userinformation.objects.get(phone=

        context={'phone':phonenum,
                 'money':updatepro.money,
                 'address':str(newaddress).rstrip(),
                 'company':str(newcompany).rstrip()}
        return render(request, 'watermarksys/profile.html', context)
    else:
        return HttpResponseRedirect('/')
@csrf_exempt
def changepass(request):
    if login_check(request) == 1:
        oldpass=request.POST['oldpass']
        newpass=request.POST['newpass']
        getusers=users.objects.get(phone=request.session['phone'])
        if(getusers.password==oldpass):
            getusers.password=newpass
            getusers.save()
            request.session['islogin']=0
            redict = {'code': 1}
            return JsonResponse(redict)
        else:
            redict={'code':0}
            return JsonResponse(redict)
    else:
        return HttpResponseRedirect("/watermarksys")
def getcookie(request):
    if(request.POST.get('id')):
        return request.POST.get('id')
    elif request.COOKIES['id']:
        return request.COOKIES['id']
    else:
        return -1
@csrf_exempt
def download(request):
    if login_check(request)==1:
        if request.method == 'POST':
            phonenum = request.session['phone']
            getid=getcookie(request)
            if(getid==-1):
                retu = {'code': 2}
                return JsonResponse(retu)
            try:
                getwater=watermark.objects.get(pk=getid)
                baseDir = os.path.dirname(os.path.abspath(__name__))  # 获取运行路径
                syspath=getwater.syspath
                wjdir=os.path.join(baseDir,"watermarksys",syspath)
                file=open(wjdir,'rb')
                respon=FileResponse(file)
                respon['Content-Type'] = 'application/octet-stream'
                respon['Content-Disposition'] = 'attachment; filename=' + getwater.filename
                respon.set_cookie('id',getid)
                return respon
            except:
                retu={'code':0}
                return JsonResponse(retu)
    else:
        return HttpResponseRedirect("/watermarksys")
@csrf_exempt
def exact(request):
    if login_check(request)==1:
        if request.method == 'POST':  # 获取对象
            obj = request.FILES.get('exactfile')
            phonenum=request.session['phone']
            filesname = str(obj.name)[-10:]
            baseDir = os.path.dirname(os.path.abspath(__name__))  # 获取运行路径
            temdir = os.path.join(baseDir, 'watermarksys', 'static', 'watermarksys', 'images', phonenum, 'temp')
            if os.path.exists(temdir):
                shutil.rmtree(temdir)
            os.makedirs(temdir)
            f = open(os.path.join(temdir, filesname), 'wb')
            for chunk in obj.chunks():
                f.write(chunk)
            f.close()
            bwm1 = WaterMark(password_wm=1, password_img=1,d1=15,d2=1)
            type=filesname[-4:]
            jpgdir=os.path.join(temdir,filesname)
            newname='new.png'
            newdir=os.path.join(temdir,newname)
            bwm1.extract(jpgdir,(64,64),newdir)
            file = open(newdir, 'rb')
            respon = FileResponse(file)
            respon['Content-Type'] = 'application/octet-stream'
            respon['Content-Disposition'] = 'attachment; filename=' + newname
            return respon
    else:
        return HttpResponseRedirect("/watermarksys")

# Create your views here.
