from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.http import HttpResponseRedirect
import tensorflow as tf
from tensorflow.keras.preprocessing import image
from django.http import FileResponse
from django.shortcuts import render,reverse
from django.views.decorators.csrf import csrf_exempt

from .models import *
import datetime
import copy
import numpy as np
from multiprocessing.dummy import Pool as ThreadPool
from pywt import dwt2, idwt2
import json
import shutil
import cv2
import qrcode
import os
class WaterMark:
    def __init__(self, password_wm=1, password_img=1, block_shape=(4, 4), cores=None,d1=1,d2=1):
        self.block_shape = np.array(block_shape)
        self.password_wm, self.password_img = password_wm, password_img  # 打乱水印和打乱原图分块的随机种子
        self.d1,self.d2=d1,d2  # d1/d2 越大鲁棒性越强,但输出图片的失真越大

        # init dat
        self.img, self.img_YUV = None, None  # self.img 是原图，self.img_YUV 对像素做了加白偶数化
        self.ca, self.hvd, = [np.array([])] * 3, [np.array([])] * 3  # 每个通道 dct 的结果
        self.ca_block = [np.array([])] * 3  # 每个 channel 存一个四维 array，代表四维分块后的结果
        self.ca_part = [np.array([])] * 3  # 四维分块后，有时因不整除而少一部分，self.ca_part 是少这一部分的 self.ca

        self.wm_size, self.block_num = 0, 0  # 水印的长度，原图片可插入信息的个数
        self.pool = ThreadPool(processes=cores)  # 水印插入分块多进程

    def init_block_index(self):
        self.block_num = self.ca_block_shape[0] * self.ca_block_shape[1]
        assert self.wm_size < self.block_num, IndexError(
            '最多可嵌入{}kb信息，多于水印的{}kb信息，溢出'.format(self.block_num / 1000, self.wm_size / 1000))
        # self.part_shape 是取整后的ca二维大小,用于嵌入时忽略右边和下面对不齐的细条部分。
        self.part_shape = self.ca_block_shape[:2] * self.block_shape
        self.block_index = [(i, j) for i in range(self.ca_block_shape[0]) for j in range(self.ca_block_shape[1])]

    def read_img(self, filename):
        # 读入图片->YUV化->加白边使像素变偶数->四维分块
        self.img = cv2.imread(filename).astype(np.float32)
        self.img_shape = self.img.shape[:2]

        # 如果不是偶数，那么补上白边
        self.img_YUV = cv2.copyMakeBorder(cv2.cvtColor(self.img, cv2.COLOR_BGR2YUV),
                                          0, self.img.shape[0] % 2, 0, self.img.shape[1] % 2,
                                          cv2.BORDER_CONSTANT, value=(0, 0, 0))

        self.ca_shape = [(i + 1) // 2 for i in self.img_shape]

        self.ca_block_shape = (self.ca_shape[0] // self.block_shape[0], self.ca_shape[1] // self.block_shape[1],
                               self.block_shape[0], self.block_shape[1])
        strides = 4 * np.array([self.ca_shape[1] * self.block_shape[0], self.block_shape[1], self.ca_shape[1], 1])

        for channel in range(3):
            self.ca[channel], self.hvd[channel] = dwt2(self.img_YUV[:, :, channel], 'haar')
            # 转为4维度
            self.ca_block[channel] = np.lib.stride_tricks.as_strided(self.ca[channel].astype(np.float32),
                                                                     self.ca_block_shape, strides)

    def read_img_wm(self, filename):
        # 读入图片格式的水印，并转为一维 bit 格式
        self.wm = cv2.imread(filename)[:, :, 0]
        # 加密信息只用bit类，抛弃灰度级别
        self.wm_bit = self.wm.flatten() > 128

    def read_wm(self, wm_content, mode='img'):
        if mode == 'img':
            self.read_img_wm(filename=wm_content)
        elif mode == 'str':
            byte = bin(int(wm_content.encode('utf-8').hex(), base=16))[2:]
            self.wm_bit = (np.array(list(byte)) == '1')
        else:
            self.wm_bit = np.array(wm_content)
        self.wm_size = self.wm_bit.size
        # 水印加密:
        np.random.RandomState(self.password_wm).shuffle(self.wm_bit)

    def block_add_wm(self, arg):
        block, shuffler, i = arg
        # dct->flatten->加密->逆flatten->svd->打水印->逆svd->逆dct
        wm_1 = self.wm_bit[i % self.wm_size]
        block_dct = cv2.dct(block)

        # 加密（打乱顺序）
        block_dct_shuffled = block_dct.flatten()[shuffler].reshape(self.block_shape)
        U, s, V = np.linalg.svd(block_dct_shuffled)
        s[0] = (s[0] // self.d1 + 1 / 4 + 1 / 2 * wm_1) * self.d1
        if self.d2:
            s[1] = (s[1] // self.d2 + 1 / 4 + 1 / 2 * wm_1) * self.d2

        block_dct_flatten = np.dot(U, np.dot(np.diag(s), V)).flatten()
        block_dct_flatten[shuffler] = block_dct_flatten.copy()
        return cv2.idct(block_dct_flatten.reshape(self.block_shape))

    def embed(self, filename):
        self.init_block_index()

        embed_ca = copy.deepcopy(self.ca)
        embed_YUV = [np.array([])] * 3
        self.idx_shuffle = np.random.RandomState(self.password_img) \
            .random(size=(self.block_num, self.block_shape[0] * self.block_shape[1])) \
            .argsort(axis=1)

        for channel in range(3):
            tmp = self.pool.map(self.block_add_wm,
                                [(self.ca_block[channel][self.block_index[i]], self.idx_shuffle[i], i)
                                 for i in range(self.block_num)])

            for i in range(self.block_num):
                self.ca_block[channel][self.block_index[i]] = tmp[i]

            # 4维分块变回2维
            self.ca_part[channel] = np.concatenate(np.concatenate(self.ca_block[channel], 1), 1)
            # 4维分块时右边和下边不能整除的长条保留，其余是主体部分，换成 embed 之后的频域的数据
            embed_ca[channel][:self.part_shape[0], :self.part_shape[1]] = self.ca_part[channel]
            # 逆变换回去
            embed_YUV[channel] = idwt2((embed_ca[channel], self.hvd[channel]), "haar")

        # 合并3通道
        embed_img_YUV = np.stack(embed_YUV, axis=2)
        # 之前如果不是2的整数，增加了白边，这里去除掉
        embed_img_YUV = embed_img_YUV[:self.img_shape[0], :self.img_shape[1]]
        embed_img = cv2.cvtColor(embed_img_YUV, cv2.COLOR_YUV2BGR)
        embed_img = np.clip(embed_img, a_min=0, a_max=255)
        cv2.imwrite(filename, embed_img)
        return embed_img

    def block_get_wm(self, args):
        block, shuffler = args
        # dct->flatten->加密->逆flatten->svd->解水印
        block_dct_shuffled = cv2.dct(block).flatten()[shuffler].reshape(self.block_shape)

        U, s, V = np.linalg.svd(block_dct_shuffled)
        wm = (s[0] % self.d1 > self.d1 / 2) * 1
        if self.d2:
            tmp = (s[1] % self.d2 > self.d2 / 2) * 1
            wm = (wm * 3 + tmp * 1) / 4
        return wm

    def extract(self, filename, wm_shape, out_wm_name=None, mode='img'):
        self.wm_size = np.array(wm_shape).prod()
        self.read_img(filename)
        self.init_block_index()

        wm_extract = np.zeros(shape=(3, self.block_num))  # 3个channel，length 个分块提取的水印，全都记录下来
        wm = np.zeros(shape=self.wm_size)  # 最终提取的水印，是 wm_extract 循环嵌入+3个 channel 的平均
        self.idx_shuffle = np.random.RandomState(self.password_img) \
            .random(size=(self.block_num, self.block_shape[0] * self.block_shape[1])) \
            .argsort(axis=1)
        for channel in range(3):
            wm_extract[channel, :] = self.pool.map(self.block_get_wm,
                                                   [(self.ca_block[channel][self.block_index[i]], self.idx_shuffle[i])
                                                    for i in range(self.block_num)])

        for i in range(self.wm_size):
            wm[i] = wm_extract[:, i::self.wm_size].mean()

        # 水印提取完成后，解密
        wm_index = np.arange(self.wm_size)
        np.random.RandomState(self.password_wm).shuffle(wm_index)
        wm[wm_index] = wm.copy()

        if mode == 'img':
            cv2.imwrite(out_wm_name, 255 * wm.reshape(wm_shape[0], wm_shape[1]))
        elif mode == 'str':
            byte = ''.join((np.round(wm)).astype(np.int).astype(np.str))
            wm = bytes.fromhex(hex(int(byte, base=2))[2:]).decode('utf-8')
        return wm
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
            model = tf.keras.models.load_model(os.path.join(baseDir, 'watermarksys','static','watermarksys','mymodel','my_resnet_model_1.h5'))
            img = image.load_img(temdir_pic, target_size=(224, 224))
            img = image.img_to_array(img) / 255.0
            img = np.expand_dims(img, axis=0)  # 为batch添加第四维
            resultrec=np.argmax(model.predict(img))
            if resultrec==0:
                bwm1 = WaterMark(password_wm=1, password_img=1,d1=15,d2=1)
            else:
                bwm1 = WaterMark(password_wm=1, password_img=1, d1=30, d2=1)
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
