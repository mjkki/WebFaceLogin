from django.urls import path
from . import views

app_name = 'facerecognition'
urlpatterns = [
    path('', views.index, name='index'),
    path('face_recognition/', views.face_recognition, name='face_recognition'),
    path('about/', views.about, name='about'),
    path('face_recognition/file_upload/', views.file_upload, name='file_upload'),
    path('face_recognition/file_merge/', views.file_merge, name='file_merge'),
    path('face_recognition/to_download/', views.to_download, name='to_download'),
    path('face_recognition/download/', views.download, name='download'),
]
