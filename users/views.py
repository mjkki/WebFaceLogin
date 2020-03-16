import base64
import datetime
import os
import cv2
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
# Create your views here.
import face_recognition
from users import models
from .forms import UserForm, RegisterForm
import hashlib


def logout(request):
    """注销用户"""
    if not request.session.get('is_login', None):
        # 如果未登录，也就没有登出一词
        return HttpResponseRedirect(reverse('facerecognition:index'))
    request.session.flush()
    return HttpResponseRedirect(reverse('facerecognition:index'))


def register(request):
    """注册新用户"""
    if request.session.get('is_login', None):
        # 登录状态不允许注册
        return HttpResponseRedirect(reverse('facerecognition:index'))
    if request.method == 'POST':
        # 显示空的注册表单
        register_form = RegisterForm(request.POST)
        message = "验证码错误！"
        if register_form.is_valid():  # 获取数据
            username = register_form.cleaned_data['username']
            password1 = register_form.cleaned_data['password1']
            password2 = register_form.cleaned_data['password2']
            email = register_form.cleaned_data['email']
            sex = register_form.cleaned_data['sex']
            if password1 != password2:  # 判断两次密码是否相同
                message = "两次输入的密码不同！"
                return render(request, 'users/register.html', locals())
            else:
                same_name_user = models.User.objects.filter(name=username)
                if same_name_user:  # 用户名唯一
                    message = '用户已经存在，请重新选择用户名！'
                    return render(request, 'users/register.html', locals())
                same_email_user = models.User.objects.filter(email=email)
                if same_email_user:  # 邮箱地址唯一
                    message = '该邮箱地址已被注册，请使用别的邮箱！'
                    return render(request, 'users/register.html', locals())

                # 当一切都OK的情况下，创建新用户
                new_user = models.User.objects.create()
                new_user.name = username
                new_user.password = hash_code(password1)  # 使用加密密码
                new_user.email = email
                new_user.sex = sex
                new_user.save()
                request.session['register_name'] = username
                # return HttpResponseRedirect(reverse('users:face_entry'))  # 自动跳转到人脸录入页面
                return render(request, 'users/face_entry.html')
    register_form = RegisterForm()
    return render(request, 'users/register.html', locals())


def login(request):
    """用户登录"""
    if request.session.get('is_login', None):
        return HttpResponseRedirect(reverse('facerecognition:index'))
    if request.method == 'POST':
        login_form = UserForm(request.POST)
        message = "所有字段都必须填写！"
        if login_form.is_valid():   # 用户名密码都不为空
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            try:
                user = models.User.objects.get(name=username)
                if user.password == hash_code(password):
                    request.session['is_login'] = True
                    request.session['user_id'] = user.id
                    request.session['user_name'] = user.name
                    return HttpResponseRedirect(reverse('facerecognition:index'))
                else:
                    message = "密码不正确！"
            except:
                message = "用户名不存在！"
        return render(request, 'users/login.html', {'message': message, 'login_form': login_form})
    login_form = UserForm()
    return render(request, 'users/login.html', {'login_form': login_form})


def hash_code(s, salt='mysite'):  # 加点盐
    """
    密码加存储
    :param s:
    :param salt:
    :return:
    """
    h = hashlib.sha256()
    s += salt
    h.update(s.encode())  # update方法只接收bytes类型
    return h.hexdigest()


def get_face(request):
    """人脸登录验证"""
    if request.POST:
        time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        strs = request.POST['message']
        imgdata = base64.b64decode(strs)
        file_path = os.path.join('users', 'static', 'face_data', 'confirm', time + ".png")
        try:
            file = open(file_path, 'wb+')
            file.write(imgdata)
            file.close()
            username = check_face('./users/static/face_data/register/', file_path)
            if username:
                # 此处会有bug，数据库用户和人脸识别用户不一致的问题
                request.session['is_login'] = True
                request.session['user_name'] = username
                return HttpResponse('index')
            else:
                return HttpResponse('no')
        except Exception as err:
            print(err)
        finally:
            delete_pic('./users/static/face_data/confirm/')
    return HttpResponse('no')


def index(request):
    """重定向到index"""
    return HttpResponseRedirect(reverse('facerecognition:index'))


def check_face(known_path, unknown_path):
    """
    用于人脸判别
    :param known_path:
    :param unknown_path:
    :return:
    """
    picture_of_known = []  # 已知的图片文件
    known_faces_encoding = []       # 已知的图片编码

    # 加载图片
    files = file_name(known_path)
    for i in range(len(files)):
        picture_of_known.append(face_recognition.load_image_file(known_path+files[i]))

    unknown_picture = face_recognition.load_image_file(unknown_path)

    # 编码图片
    for i in range(len(picture_of_known)):
        known_face_encodings = face_recognition.face_encodings(picture_of_known[i])
        if len(known_face_encodings) > 0:
            known_faces_encoding.append(known_face_encodings[0])
    # 如果没有人脸，此处会报数组越界异常
    unknown_face_encoding = face_recognition.face_encodings(unknown_picture)
    if len(unknown_face_encoding) > 0:
        unknown_face_encoding = unknown_face_encoding[0]
        # 人脸验证的结果
        results = face_recognition.compare_faces(known_faces_encoding, unknown_face_encoding, tolerance=0.5)
        for i in range(len(results)):
            if results[i]:
                file = files[i].split(".")[0]
                print("file:"+file)
                return file
    return None


def delete_pic(path):
    """
    文件数量超过限制，删除一个文件
    :param path:
    :return:
    """
    files = os.listdir(path)
    files.sort()
    imgCount = files.__len__()
    if imgCount > 10:
        # 图片超过10个，删除一个
        os.unlink(path + files[0])


def file_name(file_dir):
    """
    遍历文件夹"
    :param file_dir: 
    :return: 
    """""
    for root, dirs, files in os.walk(file_dir):
        pass
    return files


def face_entry(request):
    """人脸录入界面"""
    return render(request, 'users/face_entry.html')


def face_entry_getface(request):
    """保存注册的截图"""
    if request.method == 'POST':
        print("begin保存注册的截图")
        register_name = request.session.get('register_name')
        strs = request.POST['message']
        imgdata = base64.b64decode(strs)
        file_path = os.path.join('users', 'static', 'face_data', 'register', register_name + ".png")
        try:
            file = open(file_path, 'wb+')
            file.write(imgdata)
            file.close()
        except Exception as err:
            print(err)
        if shape_pic(file_path):
            # request.session['register_name'] = None
            return HttpResponse('login')  # 自动跳转到登录页面
        return HttpResponse('no')


def face_entry_login(request):
    """重定向到login页面"""
    return HttpResponseRedirect(reverse('users:login'))


def shape_pic(pic_path):
    """
    裁剪照片
    :param pic_path:
    :return:
    """
    src = cv2.imread(pic_path)
    grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
    # 告诉OpenCV使用人脸识别分类器
    classfier = cv2.CascadeClassifier("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml")
    # 人脸检测，1.2和2分别为图片缩放比例和需要检测的有效点数
    faceRects = classfier.detectMultiScale(grey, scaleFactor=1.2, minNeighbors=3, minSize=(32, 32))
    if len(faceRects) > 0:  # 大于0则检测到人脸
        for faceRect in faceRects:  # 单独框出每一张人脸
            x, y, w, h = faceRect
            image = src[y - 10:y + h + 10, x - 10:x + w + 10]
            cv2.imwrite(pic_path, image)
            return True
    return False

