from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def is_student_user(user):
    return user.is_authenticated and hasattr(user, "student") and not is_faculty_user(user)


def is_faculty_user(user):
    return user.is_authenticated and hasattr(user, "faculty")


def is_admin_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def can_manage_complaints(user):
    return is_faculty_user(user) or is_admin_user(user)


def student_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if can_manage_complaints(request.user):
            return redirect("faculty_dashboard")
        if not is_student_user(request.user):
            messages.error(request, "Please complete student registration before continuing.")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return wrapper


def faculty_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not can_manage_complaints(request.user):
            messages.error(request, "You do not have permission to open the faculty portal.")
            return redirect("student_dashboard" if is_student_user(request.user) else "faculty_login")
        return view_func(request, *args, **kwargs)

    return wrapper


admin_required = faculty_required
