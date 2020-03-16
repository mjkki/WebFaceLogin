import os, shutil
import zipfile
from django.urls import reverse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
# Create your views here.
from django.views.decorators.csrf import csrf_exempt
import cv2
import numpy as np
from django.http import FileResponse


def index(request):
    """index界面"""
    return render(request, 'facerecognition/index.html')


def face_recognition(request):
    """用于人脸模糊的页面"""
    if request.session.get('is_login', None):
        return render(request, 'facerecognition/face_recognition.html')
    else:
        return HttpResponseRedirect(reverse('users:login'))  # 自动跳转到登录页面


def about(request):
    """定位到关于本站页面"""
    return render(request, 'facerecognition/about.html')


@csrf_exempt
def file_upload(request):
    """用于处理上传文件"""
    if request.method == 'POST':
        upload_file = request.FILES.get('file')
        chunk = request.POST.get('chunk', 0)  # 获取该分片在所有分片中的序号
        if chunk != 0:
            filename = upload_file.name
            request.session['filename'] = filename  # 分片上传的标志
            filename = '%s%s' % (filename, chunk)  # 构成该分片唯一标识符
        else:
            filename = upload_file.name
        username = request.session.get('user_name')
        default_storage.save('./upload/%s/%s' % (username, filename), ContentFile(upload_file.read()))  # 保存分片到本地
    return HttpResponse('face_recognition.html', locals())


@csrf_exempt
def file_merge(request):
    """整合分片上传的文件"""
    filename = request.session.get('filename')
    username = request.session.get('user_name')
    # 若有分块上传的文件，则对文件进行整合
    if filename:
        upload_file = filename.split(".")[0]
        join_file("./upload/%s/" % username, filename, "./upload/%s/" % username, upload_file)
        request.session['filename'] = None
    else:
        pass
    # 遍历所有文件，对视频和图片进行人脸模糊处理
    in_dir = "./upload/%s/" % username
    out_dir = "./download/%s/" % username
    if not os.path.exists(out_dir):
        os.mkdir(out_dir)
    in_files = os.listdir(in_dir)
    in_files.sort()
    for file in in_files:
        in_path = os.path.join(in_dir, file)
        out_path = os.path.join(out_dir, file)
        if file.split(".")[1] == 'mp4':
            # print("注释掉了mp4!!!!")
            blur_video(out_path, in_path)
        else:
            blur_image(out_path, in_path)
    # 对文件进行压缩
    zip_ya(out_dir, "./download/%s.zip" % username)
    return HttpResponse('to_download')


def to_download(request):
    return render(request, 'facerecognition/download.html')


def download(request):
    username = request.session.get('user_name')
    down_dir = "./download/"
    filename = username + ".zip"
    path = os.path.join(down_dir, filename)
    file = open(path, 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = 'attachment;filename="%s"' % filename
    # 删除已经处理完成的图片
    path = "./upload/%s/" % username
    delete_done(path)
    return response


def join_file(from_dir, filename, to_dir, upload_file):
    """
    将分片上传的文件整合
    :param from_dir:需要整合的文件所在的文件夹
    :param filename:输出的文件名
    :param to_dir:整合后输出的文件夹
    :param upload_file:除去后缀后的文件名
    :return:
    """
    if not os.path.exists(to_dir):
        os.mkdir(to_dir)
    if not os.path.exists(from_dir):
        print('Wrong directory')
    outfile = open(os.path.join(to_dir, filename), 'wb')
    files = os.listdir(from_dir)
    files.sort()
    flag = False
    for file in files:
        if upload_file == file.split(".")[0]:
            file_path = os.path.join(from_dir, file)
            infile = open(file_path, 'rb')
            data = infile.read()
            outfile.write(data)
            infile.close()
            if flag:
                os.remove(file_path)
            flag = True
    outfile.close()


def blur_image(filename, file_path):
    """
    图片人脸部分模糊
    :param filename:人脸模糊后的输出路径
    :param file_path: 读取文件的路径
    :return:
    """
    classfier = cv2.CascadeClassifier("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml")
    src = cv2.imread(file_path)
    grey = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

    # 人脸检测，1.2和2分别为图片缩放比例和需要检测的有效点数
    faceRects = classfier.detectMultiScale(grey, scaleFactor=1.2, minNeighbors=3, minSize=(32, 32))
    if len(faceRects) > 0:  # 大于0则检测到人脸
        for faceRect in faceRects:  # 单独框出每一张人脸
            x, y, w, h = faceRect
            image = src[y - 10:y + h + 10, x - 10:x + w + 10]  # 截取人脸部分
            dst = np.empty(image.shape, dtype=np.uint8)        # 空白numpy数组
            cv2.blur(image, (25, 25), dst)                     # 均值滤波,输出微dst
            src[y - 10:y + h + 10, x - 10:x + w + 10] = dst
    # 保存图像
    cv2.imwrite(filename, src)


def blur_video(filename, file_path):
    """
    视频人脸部分模糊
    :param filename: 人脸模糊后的输出路径
    :param file_path: 读取文件的路径
    :return:
    """
    # 视频来源，可以来自一段已存好的视频，也可以直接来自USB摄像头
    cap = cv2.VideoCapture(file_path)
    # 告诉OpenCV使用人脸识别分类器
    classfier = cv2.CascadeClassifier("/usr/local/share/OpenCV/haarcascades/haarcascade_frontalface_alt2.xml")
    # 获得码率及尺寸
    fps = cap.get(cv2.CAP_PROP_FPS)
    size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    output_movie = cv2.VideoWriter(filename, fourcc, fps, size)

    while cap.isOpened():
        ok, frame = cap.read()  # 读取一帧数据
        if not ok:
            break
            # 将当前帧转换成灰度图像
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # 人脸检测，1.2和2分别为图片缩放比例和需要检测的有效点数
        faceRects = classfier.detectMultiScale(grey, scaleFactor=1.2, minNeighbors=3, minSize=(32, 32))
        if len(faceRects) > 0:  # 大于0则检测到人脸
            for faceRect in faceRects:  # 单独框出每一张人脸
                x, y, w, h = faceRect
                image = frame[y - 10:y + h + 10, x - 10:x + w + 10]
                dst = np.empty(image.shape, dtype=np.uint8)
                cv2.blur(image, (15, 15), dst)  # 均值滤波
                frame[y - 10:y + h + 10, x - 10:x + w + 10] = dst
                # cv2.rectangle(frame, (x - 10, y - 10), (x + w + 10, y + h + 10), color, 2)
                output_movie.write(frame)


def zip_ya(startdir, file_news):
    """
    压缩文件
    :param startdir: 要压缩的文件夹路径
    :param file_news:压缩后文件夹的名字
    """
    z = zipfile.ZipFile(file_news, 'w', zipfile.ZIP_DEFLATED)  # 参数一：文件夹名
    for dirpath, dirnames, filenames in os.walk(startdir):
        fpath = dirpath.replace(startdir, '')  # 这一句很重要，不replace的话，就从根目录开始复制
        fpath = fpath and fpath + os.sep or ''  # 这句话理解我也点郁闷，实现当前文件夹以及包含的所有文件的压缩
        for filename in filenames:
            z.write(os.path.join(dirpath, filename), fpath+filename)
    z.close()
    # 删除被压缩的原文件夹
    shutil.rmtree(startdir)


def delete_done(path):
    """
    删除已经处理完成的图片及视频
    :param path: 文件路径
    """
    try:
        shutil.rmtree(path)
    except Exception as err:
        print(err)
