"""
URL configuration for pyhomework project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from app.views import *
from allauth.account import views as account_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('neo4j-data/', get_neo4j_data, name='neo4j_data'),  # 获取neo4j的节点和边信息 ?searchTerm=... 表示只获取相关节点和边的信息
    path('click-node/', click_node), # 点击图谱节点展示课程信息
    

path('accounts/signup/', CustomSignupView.as_view(), name='account_signup'),

# 覆盖allauth的密码修改URL
    path('accounts/', include('allauth.urls')),

    path('accounts/password_change/',
         account_views.PasswordChangeView.as_view(),
         name='account_change_password'), # 原accounts/password/change路径深度造成static文件获取错误
    path('', home_view, name='home'),  # 首页（图谱）

path('delete-node/', delete_node, name='delete_node'),

# wsq新增：收藏功能
path("favorite-course/", favorite_course, name="favorite_course"),
path("my-favorites/", favorite_courses_view, name="favorite_courses"),
path("unfavorite-course/", unfavorite_course, name="unfavorite_course"),

path('add-child-node/', add_child_node, name='add_child_node'),
path('update-node-name/', update_node_name, name='update_node_name'),
path('add-course/', add_course, name='add_course'),

path('profile/', profile_view, name='profile'),  
path("recommend-users/", recommend_users, name="recommend_users"),
]



 # apps/users/urls.py  
# from django.urls import path  
# from . import views  

# app_name = 'users'  
# urlpatterns = [  
#     path('profile/', views.profile_view, name='profile'),  
# ]  