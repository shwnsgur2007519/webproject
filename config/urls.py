from django.contrib import admin
from django.urls import path, include
from Calendar import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('calendar/', include('Calendar.urls')),
    path('common/', include('common.urls')),
    path('',views.index, name='index')
]
