from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .forms import CustomUserCreationForm
from .models import User

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('calendar:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'common/signup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('calendar:index')

def user_page(request, username):
    user = get_object_or_404(User, username=username)

    context = {
        'user_profile': user,
        'is_owner': request.user == user,
    }
    return render(request, 'common/user_page.html', context)

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

@login_required
def user_edit(request, username):
    user = get_object_or_404(User, username=username)

    if request.user != user:
        return redirect('common:user_page', username=username)

    if request.method == "POST":
        pw_form = PasswordChangeForm(user, request.POST)
        if pw_form.is_valid():
            pw_form.save()
            update_session_auth_hash(request, user)
            return redirect('common:user_page', username=user.username)
        # 여기서 else 없이 pw_form 그대로 아래로 넘김
    else:
        pw_form = PasswordChangeForm(user)

    # GET이든, POST 실패든 여기서 렌더링
    return render(request, 'common/user_edit.html', {
        'pw_form': pw_form,
        'user_profile': user,
    })
