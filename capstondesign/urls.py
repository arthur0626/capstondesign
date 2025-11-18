"""
URL configuration for capstondesign project.

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
from firstapp import views

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.generate_images, name='main'),
    # 로그인/로그아웃/회원가입
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', views.signup, name='signup'),
    
    path('profile/', views.profile, name='profile'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('profile/<int:user_id>/', views.view_user_profile, name='view_user'),

    # 프리셋 관련 URL 패턴
    path('preset/save/', views.preset_save, name='preset_save'),
    path('preset/load/<int:preset_id>/', views.preset_load, name='preset_load'),
    path('preset/delete/<int:preset_id>/', views.preset_delete, name='preset_delete'),

    # 이미지 분석, 편집, 동영상 변환
    path('analyze/', views.image_analyze, name='image_analyze'),
    path('edit/', views.image_edit, name='image_edit'),
    path('video/', views.image_to_video, name='image_to_video'), 
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)