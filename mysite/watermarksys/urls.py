from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login',views.login,name='login'),
    #页面跳转
    path('getregister',views.getregister,name='getregister'),
    path('getaccount',views.getaccount,name='getaccount'),
    path('getprofile',views.getprofile,name='getprofile'),
    path('getindex',views.getindex,name='getindex'),
    path('gethistory',views.gethistory,name='gethistory'),

    #功能实现
    path('embed',views.embed,name='embed'),
    path('register',views.register,name='register'),
    path('loginout',views.loginout,name='loginout'),
    path('updateprofile',views.updateprofile,name='updateprofile'),
    path('changepass',views.changepass,name='changepass'),
    path('download',views.download,name='download'),
    path('exact',views.exact,name='exact'),
]