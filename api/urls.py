"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.conf.urls import url, include
from django.contrib import admin
from django.urls import path
from .api import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'players', views.PlayerViewSet)
router.register(r'damage-types', views.DamageTypeViewSet)
router.register(r'rounds', views.RoundViewSet)
router.register(r'frags', views.FragViewSet)
router.register(r'maps', views.MapViewSet)
router.register(r'logs', views.LogViewSet)
router.register(r'events', views.EventViewSet)
router.register(r'patrons', views.PatronViewSet)
router.register(r'announcements', views.AnnouncementViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    path('reports/damage_type_friendly_fire/', views.damage_type_friendly_fire),
    # path('reports/top10/', views.top10),
    path('reports/easter/', views.easter),
    path('admin/', admin.site.urls),
]
