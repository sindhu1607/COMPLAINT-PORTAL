from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.StudentLoginView.as_view(), name="login"),
    path("faculty/login/", views.FacultyLoginView.as_view(), name="faculty_login"),
    path("admin-login/", views.FacultyLoginView.as_view(), name="admin_login"),
    path("register/", views.student_register, name="register"),
    path("faculty/register/", views.faculty_register, name="faculty_register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(template_name="registration/password_reset_form.html"),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("profile/", views.profile, name="profile"),
    path("notifications/read/", views.mark_notifications_read, name="mark_notifications_read"),
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("complaints/", views.complaint_list, name="complaint_list"),
    path("complaints/new/", views.complaint_create, name="complaint_create"),
    path("complaints/<int:pk>/", views.complaint_detail, name="complaint_detail"),
    path("complaints/<int:pk>/edit/", views.complaint_edit, name="complaint_edit"),
    path("complaints/<int:pk>/delete/", views.complaint_delete, name="complaint_delete"),
    path("complaints/<int:pk>/comment/", views.add_comment, name="add_comment"),
    path("complaints/<int:pk>/reopen/", views.reopen_complaint, name="reopen_complaint"),
    path("complaints/<int:pk>/feedback/", views.submit_feedback, name="submit_feedback"),
    path("complaints/<int:pk>/status-json/", views.complaint_status_json, name="complaint_status_json"),
    path("faculty/dashboard/", views.faculty_dashboard, name="faculty_dashboard"),
    path("faculty/complaints/", views.faculty_complaint_list, name="faculty_complaint_list"),
    path("faculty/complaints/<int:pk>/accept/", views.faculty_accept_complaint, name="faculty_accept_complaint"),
    path("faculty/complaints/<int:pk>/update/", views.faculty_update_complaint, name="faculty_update_complaint"),
    path("faculty/feedback/", views.feedback_analytics, name="feedback_analytics"),
    path("faculty/export/", views.export_complaints_csv, name="export_complaints_csv"),
    path("portal-admin/dashboard/", views.faculty_dashboard, name="admin_dashboard"),
    path("portal-admin/complaints/", views.faculty_complaint_list, name="admin_complaint_list"),
    path("portal-admin/complaints/<int:pk>/update/", views.faculty_update_complaint, name="admin_update_complaint"),
    path("portal-admin/export/", views.export_complaints_csv, name="admin_export_complaints_csv"),
]
