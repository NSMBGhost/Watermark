from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login',views.login,name='login'),
    path('getregister',views.getregister,name='getregister'),

    path('getaccount',views.getaccount,name='getaccount'),
    path('getprofile',views.getprofile,name='getprofile'),
    path('getindex',views.getindex,name='getindex'),
    path('gethistory',views.gethistory,name='gethistory'),
    path('embed',views.embed,name='embed'),
    path('register',views.register,name='register'),
    path('loginout',views.loginout,name='loginout')
]