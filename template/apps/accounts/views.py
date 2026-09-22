from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator

from apps.core.ratelimit import ratelimit

from . import forms


@method_decorator(ratelimit("login", rate="10/5m"), name="dispatch")
class LoginView(auth_views.LoginView):
    # Şablon adları açıkça verilir: django.contrib.admin'in registration/* şablonları gölgelemesin.
    template_name = "accounts/login.html"
    form_class = forms.LoginForm
    redirect_authenticated_user = True


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = forms.PasswordChangeForm
    success_url = reverse_lazy("pages:home")

    def form_valid(self, form):
        messages.success(self.request, "Şifreniz güncellendi.")
        return super().form_valid(form)


@method_decorator(ratelimit("password-reset", rate="5/h"), name="dispatch")
class PasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset.html"
    form_class = forms.PasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")

    @property
    def extra_email_context(self):
        return {"project_name": settings.SITE_NAME}


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = forms.SetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


@ratelimit("signup", rate="5/h")
def signup(request):
    if not settings.ACCOUNTS_ALLOW_SIGNUP:
        raise Http404
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    form = forms.SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Hesabınız oluşturuldu. Hoş geldiniz!")
        return redirect(settings.LOGIN_REDIRECT_URL)
    status = 422 if form.is_bound else 200
    return render(request, "accounts/signup.html", {"form": form}, status=status)
