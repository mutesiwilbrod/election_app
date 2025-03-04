"""
URL configuration for election_tally project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from tally.views import login_view, dashboard_view, submit_results_view, edit_results_view

urlpatterns = [
    path('admin/', admin.site.urls),         # Django admin panel
    path('api/', include('tally.urls')),       # API endpoints
    path('login/', login_view, name='login'),  # Login view
    path('dashboard/', dashboard_view, name='dashboard'), # Dashboard view
    path('submit_results/', submit_results_view, name='submit_results'),
    path('edit_results/', edit_results_view, name='edit_results'),

]