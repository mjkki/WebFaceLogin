from django.urls import path, include
from . import views

app_name = 'users'
urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('register/', views.register, name='register'),

    path('login/get_face/', views.get_face, name='get_face'),
    path('login/index/', views.index, name='login_index'),

    # path('face_entry/', views.face_entry, name='face_entry'),
    path('register/face_entry_getface/', views.face_entry_getface, name='face_entry_getface'),
    path('register/login/', views.face_entry_login, name='face_entry_login'),
]
