"""
URL configuration for myproject project.

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
# myproject/urls.py
from dashboard import views  
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView  # ✅ Add this
from dashboard.views import home_redirect

urlpatterns = [
    path('', home_redirect, name='home'),  # root URL will redirect to admin-dashboard/
    path('admin/', admin.site.urls),
    path('admin-dashboard/', include('dashboard.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('notifications/', views.notification_center, name='notification_center'),

    # ✅ Add this if you want /login/ to work
    path('login/', RedirectView.as_view(url='/accounts/login/')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
