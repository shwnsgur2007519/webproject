from django.urls import path
from . import views

app_name='calendar'

urlpatterns = [
    path('', views.index, name='index'),
    path('schedule/create/', views.schedule_create, name='schedule_create'),
    path('schedule/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    path('schedule/list/', views.schedule_list, name='schedule_list'),
    path('schedule/type_create/', views.schedule_type_create, name='schedule_type_create'),
    path('schedule-type/list/', views.schedule_type_list, name='schedule_type_list'),
    path('schedule-type/<int:pk>/edit/', views.schedule_type_edit, name='schedule_type_edit'),
    path('schedule-type/<int:pk>/delete/', views.schedule_type_delete, name='schedule_type_delete'),
    path('week/', views.schedule_week, name='schedule_week'),
    path('schedule/<int:pk>/mark_done/', views.schedule_mark_done, name='schedule_mark_done'),
    path('schedule/<int:pk>/unmark_done/', views.schedule_unmark_done, name='schedule_unmark_done'),
    path('schedule/<int:pk>/delete/', views.schedule_delete, name='schedule_delete'),
    path('schedule/replace/', views.schedule_replace, name='schedule_replace'),
    path('schedule/replace/ai_run', views.ai_run, name='ai_run'),
    path('schedule/replace/ai_confirm', views.ai_confirm, name='ai_confirm'),
    path('schedule/replace/ai_cancel', views.ai_cancel, name='ai_cancel'),
    path('schedule/how_to_use', views.how_to_use, name='how_to_use'),
    path('schedule/test', views.test, name='test'),
    path('schedule/<int:pk>/duplicate/', views.schedule_duplicate, name='schedule_duplicate'),
]
