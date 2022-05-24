"""budgetapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
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
from django.urls import path, include
from django.contrib import admin
from budget import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('newurl', views.newurl, name='newurl'),
    path('budget', views.budget, name='budget'),
    path('results', views.results, name='results'),
    path('email', views.email, name='email'),
    path('dashboard', views.dashboard, name='dashboard'),
    path('transactions', views.transactions, name='transactions'),
    path('', views.homepage, name='homepage'),
    path('setup', views.index, name='index'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
