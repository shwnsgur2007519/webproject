from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name='common'

urlpatterns=[
    path('login/', auth_views.LoginView.as_view(template_name='common/login.html'), name='login'),
    path('logout/',views.logout_view, name='logout'),
    path('signup/',views.signup, name='signup'),
    path('user/<str:username>/', views.user_page, name="user_page"),
    path('user/<str:username>/edit/', views.user_edit, name="user_edit"),
]