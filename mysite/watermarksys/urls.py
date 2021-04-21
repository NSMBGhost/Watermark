from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login',views.login,name='login'),
    path('getregister',views.getregister,name='getregister'),
    path('getfileload',views.getfileload,name='getfileload'),
    path('embed',views.embed,name='embed'),
]