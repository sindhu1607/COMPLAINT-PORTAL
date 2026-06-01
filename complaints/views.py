import csv
import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import can_manage_complaints, faculty_required, is_admin_user, is_student_user, student_required
from .forms import (
    ComplaintCommentForm,
    ComplaintFilterForm,
    ComplaintForm,
    FacultyAuthenticationForm,
    FacultyProfileForm,
    FacultyRegistrationForm,
    FeedbackForm,
    StatusUpdateForm,
    StudentAuthenticationForm,
    StudentProfileForm,
    StudentRegistrationForm,
    UserUpdateForm,
)
from .models import (
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintStatusHistory,
    Department,
    Faculty,
    Feedback,
    Notification,
    Student,
)
from .services import build_workflow_steps, notify_user, record_initial_submission, record_status


class StudentLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = StudentAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("student_dashboard")


class FacultyLoginView(LoginView):
    template_name = "auth/faculty_login.html"
    authentication_form = FacultyAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("faculty_dashboard")


AdminLoginView = FacultyLoginView


def home(request):
    if request.user.is_authenticated:
        if can_manage_complaints(request.user):
            return redirect("faculty_dashboard")
        if is_student_user(request.user):
            return redirect("student_dashboard")
    stats = {
        "categories": ComplaintCategory.objects.filter(is_active=True).count(),
        "departments": Department.objects.filter(is_active=True).count(),
        "resolved": Complaint.objects.filter(status__in=[Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED]).count(),
    }
    return render(request, "landing.html", stats)


def student_register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Your student account is ready.")
            return redirect("student_dashboard")
    else:
        form = StudentRegistrationForm()
    return render(request, "auth/register.html", {"form": form})


def faculty_register(request):
    if request.method == "POST":
        form = FacultyRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Faculty profile created. You can now manage assigned complaints.")
            return redirect("faculty_dashboard")
    else:
        form = FacultyRegistrationForm()
    return render(request, "auth/faculty_register.html", {"form": form})


StudentRegisterView = student_register


def _terminal_status_filter():
    return [Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED, Complaint.STATUS_REJECTED]


@student_required
def student_dashboard(request):
    complaints = Complaint.objects.filter(student=request.user)
    total = complaints.count()
    pending = complaints.exclude(status__in=_terminal_status_filter()).count()
    resolved = complaints.filter(status__in=[Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED]).count()
    emergency = complaints.filter(priority=Complaint.PRIORITY_EMERGENCY).count()
    feedback_due = complaints.filter(status=Complaint.STATUS_RESOLVED, feedback__isnull=True).count()
    recent = complaints.select_related("category", "assigned_department", "assigned_faculty__user")[:6]
    notifications = request.user.notifications.filter(is_read=False)[:5]

    context = {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "emergency": emergency,
        "feedback_due": feedback_due,
        "recent_complaints": recent,
        "notifications": notifications,
    }
    return render(request, "dashboards/student_dashboard.html", context)


def _filter_complaints(queryset, form):
    if form.is_valid():
        q = form.cleaned_data.get("q")
        category = form.cleaned_data.get("category")
        status = form.cleaned_data.get("status")
        priority = form.cleaned_data.get("priority")
        department = form.cleaned_data.get("department")

        if q:
            queryset = queryset.filter(
                Q(ticket_id__icontains=q)
                | Q(title__icontains=q)
                | Q(student__first_name__icontains=q)
                | Q(student__last_name__icontains=q)
                | Q(student__email__icontains=q)
            )
        if category:
            queryset = queryset.filter(category=category)
        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if department:
            queryset = queryset.filter(assigned_department=department)
    return queryset


def _faculty_complaint_queryset(user):
    queryset = Complaint.objects.select_related(
        "student",
        "student__student",
        "category",
        "assigned_department",
        "assigned_faculty",
        "assigned_faculty__user",
    )
    if is_admin_user(user):
        return queryset
    faculty = getattr(user, "faculty", None)
    if not faculty:
        return queryset.none()
    department_filter = Q()
    if faculty.department_id:
        department_filter = Q(assigned_department=faculty.department)
    return queryset.filter(Q(assigned_faculty=faculty) | department_filter).distinct()


@student_required
def complaint_list(request):
    form = ComplaintFilterForm(request.GET or None)
    complaints = Complaint.objects.filter(student=request.user).select_related(
        "category", "assigned_department", "assigned_faculty__user"
    )
    complaints = _filter_complaints(complaints, form)
    paginator = Paginator(complaints, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "complaints/complaint_list.html",
        {"form": form, "page_obj": page_obj, "complaints": page_obj.object_list},
    )


@student_required
def complaint_create(request):
    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.student = request.user
            if not complaint.assigned_department and complaint.category.department:
                complaint.assigned_department = complaint.category.department
            complaint.save()
            for file in form.cleaned_data.get("attachments", []):
                ComplaintAttachment.objects.create(
                    complaint=complaint,
                    uploaded_by=request.user,
                    file=file,
                )
            record_initial_submission(complaint)
            messages.success(request, f"Complaint {complaint.ticket_id} submitted successfully.")
            return redirect("complaint_detail", pk=complaint.pk)
    else:
        form = ComplaintForm()
    return render(request, "complaints/complaint_form.html", {"form": form, "mode": "create"})


@student_required
def complaint_edit(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.user)
    if not complaint.can_student_edit:
        messages.error(request, "This complaint is already under review and can no longer be edited.")
        return redirect("complaint_detail", pk=pk)

    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES, instance=complaint)
        if form.is_valid():
            complaint = form.save()
            for file in form.cleaned_data.get("attachments", []):
                ComplaintAttachment.objects.create(complaint=complaint, uploaded_by=request.user, file=file)
            messages.success(request, "Complaint updated.")
            return redirect("complaint_detail", pk=complaint.pk)
    else:
        form = ComplaintForm(instance=complaint)
    return render(request, "complaints/complaint_form.html", {"form": form, "complaint": complaint, "mode": "edit"})


@student_required
def complaint_delete(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.user)
    if not complaint.can_student_edit:
        messages.error(request, "This complaint is already accepted and cannot be deleted.")
        return redirect("complaint_detail", pk=pk)
    if request.method == "POST":
        ticket_id = complaint.ticket_id
        complaint.delete()
        messages.success(request, f"Complaint {ticket_id} deleted.")
        return redirect("complaint_list")
    return render(request, "complaints/complaint_confirm_delete.html", {"complaint": complaint})


def _get_visible_complaint(request, pk):
    queryset = Complaint.objects.select_related(
        "student",
        "student__student",
        "category",
        "assigned_department",
        "assigned_faculty",
        "assigned_faculty__user",
    ).prefetch_related(
        "attachments",
        "comments__user",
        "status_history__changed_by",
    )
    if can_manage_complaints(request.user):
        if is_admin_user(request.user):
            return get_object_or_404(queryset, pk=pk)
        return get_object_or_404(_faculty_complaint_queryset(request.user).prefetch_related("attachments", "comments__user", "status_history__changed_by"), pk=pk)
    return get_object_or_404(queryset, pk=pk, student=request.user)


@login_required
def complaint_detail(request, pk):
    complaint = _get_visible_complaint(request, pk)
    comment_form = ComplaintCommentForm()
    status_form = StatusUpdateForm(instance=complaint, user=request.user) if can_manage_complaints(request.user) else None
    feedback_instance = getattr(complaint, "feedback", None)
    feedback_form = FeedbackForm(instance=feedback_instance) if complaint.student == request.user else None
    student_profile = getattr(complaint.student, "student", None)

    return render(
        request,
        "complaints/complaint_detail.html",
        {
            "complaint": complaint,
            "student_profile": student_profile,
            "comment_form": comment_form,
            "status_form": status_form,
            "feedback_form": feedback_form,
            "workflow_steps": build_workflow_steps(complaint),
            "is_faculty_area": can_manage_complaints(request.user),
        },
    )


@login_required
@require_POST
def add_comment(request, pk):
    complaint = _get_visible_complaint(request, pk)
    form = ComplaintCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.complaint = complaint
        comment.user = request.user
        comment.is_faculty_reply = can_manage_complaints(request.user)
        comment.is_admin_reply = comment.is_faculty_reply
        comment.save()
        if comment.is_faculty_reply:
            notify_user(
                complaint.student,
                f"New faculty reply on {complaint.ticket_id}",
                comment.message,
                complaint=complaint,
            )
        elif complaint.assigned_faculty:
            notify_user(
                complaint.assigned_faculty.user,
                f"Student replied on {complaint.ticket_id}",
                comment.message,
                complaint=complaint,
            )
        messages.success(request, "Comment added.")
    else:
        messages.error(request, "Please enter a valid comment.")
    return redirect("complaint_detail", pk=complaint.pk)


@student_required
@require_POST
def reopen_complaint(request, pk):
    complaint = get_object_or_404(Complaint, pk=pk, student=request.user)
    if complaint.status not in [Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED, Complaint.STATUS_REJECTED]:
        messages.info(request, "Only resolved or closed complaints can be reopened.")
        return redirect("complaint_detail", pk=pk)

    complaint.is_reopened = True
    complaint.reopened_at = timezone.now()
    complaint.save(update_fields=["is_reopened", "reopened_at", "updated_at"])
    record_status(
        complaint,
        Complaint.STATUS_IN_PROGRESS,
        changed_by=request.user,
        note="Complaint reopened by student because the issue persists.",
    )
    if complaint.assigned_faculty:
        notify_user(
            complaint.assigned_faculty.user,
            f"{complaint.ticket_id} reopened",
            "The student reopened this complaint for further action.",
            complaint=complaint,
        )
    messages.success(request, "Complaint reopened for further review.")
    return redirect("complaint_detail", pk=pk)


@student_required
@require_POST
def submit_feedback(request, pk):
    complaint = get_object_or_404(
        Complaint,
        pk=pk,
        student=request.user,
        status__in=[Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED],
    )
    instance = getattr(complaint, "feedback", None)
    form = FeedbackForm(request.POST, instance=instance)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.complaint = complaint
        feedback.student = request.user
        feedback.save()
        if not feedback.was_resolved:
            record_status(
                complaint,
                Complaint.STATUS_IN_PROGRESS,
                changed_by=request.user,
                note="Student feedback says the problem is not resolved.",
            )
        else:
            record_status(
                complaint,
                Complaint.STATUS_CLOSED,
                changed_by=request.user,
                note="Student confirmed resolution through feedback.",
            )
        messages.success(request, "Thank you for your feedback.")
    else:
        messages.error(request, "Please complete the feedback form.")
    return redirect("complaint_detail", pk=pk)


@login_required
def complaint_status_json(request, pk):
    complaint = _get_visible_complaint(request, pk)
    latest_history = complaint.status_history.last()
    return JsonResponse(
        {
            "ticket_id": complaint.ticket_id,
            "status": complaint.status,
            "status_display": complaint.get_status_display(),
            "updated_at": complaint.updated_at.strftime("%d %b %Y, %I:%M %p"),
            "latest_note": latest_history.note if latest_history else "",
        }
    )


@login_required
def profile(request):
    if is_student_user(request.user):
        profile_obj, _ = Student.objects.get_or_create(user=request.user, defaults={"roll_number": request.user.username})
        profile_form_class = StudentProfileForm
    elif can_manage_complaints(request.user) and hasattr(request.user, "faculty"):
        profile_obj = request.user.faculty
        profile_form_class = FacultyProfileForm
    else:
        messages.error(request, "No editable role profile exists for this account.")
        return redirect("home")

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = profile_form_class(request.POST, request.FILES, instance=profile_obj)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = profile_form_class(instance=profile_obj)
    return render(request, "auth/profile.html", {"user_form": user_form, "profile_form": profile_form})


@login_required
@require_POST
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, "Notifications marked as read.")
    return redirect(request.POST.get("next") or "home")


@faculty_required
def faculty_dashboard(request):
    complaints = _faculty_complaint_queryset(request.user)
    total = complaints.count()
    pending = complaints.exclude(status__in=_terminal_status_filter()).count()
    resolved = complaints.filter(status__in=[Complaint.STATUS_RESOLVED, Complaint.STATUS_CLOSED]).count()
    emergency = complaints.filter(priority=Complaint.PRIORITY_EMERGENCY).count()
    assigned_to_me = 0
    if hasattr(request.user, "faculty"):
        assigned_to_me = complaints.filter(assigned_faculty=request.user.faculty).count()

    category_counts = list(
        ComplaintCategory.objects.filter(complaints__in=complaints)
        .annotate(total=Count("complaints", filter=Q(complaints__in=complaints)))
        .values("name", "total")
        .order_by("name")
    )
    monthly_counts = list(
        complaints.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Count("id"))
        .order_by("month")
    )
    rating_summary = Feedback.objects.filter(complaint__in=complaints).aggregate(avg_rating=Avg("rating"), total=Count("id"))
    recent = complaints[:7]
    stale_since = timezone.now() - timedelta(days=7)
    stale_count = complaints.filter(created_at__lt=stale_since).exclude(status__in=_terminal_status_filter()).count()

    context = {
        "total": total,
        "pending": pending,
        "resolved": resolved,
        "emergency": emergency,
        "assigned_to_me": assigned_to_me,
        "stale_count": stale_count,
        "avg_rating": round(rating_summary["avg_rating"] or 0, 1),
        "feedback_total": rating_summary["total"],
        "recent_complaints": recent,
        "category_labels": json.dumps([row["name"] for row in category_counts]),
        "category_values": json.dumps([row["total"] for row in category_counts]),
        "monthly_labels": json.dumps([row["month"].strftime("%b %Y") for row in monthly_counts if row["month"]]),
        "monthly_values": json.dumps([row["total"] for row in monthly_counts if row["month"]]),
    }
    return render(request, "dashboards/faculty_dashboard.html", context)


admin_dashboard = faculty_dashboard


@faculty_required
def faculty_complaint_list(request):
    form = ComplaintFilterForm(request.GET or None, include_department=True)
    complaints = _faculty_complaint_queryset(request.user)
    complaints = _filter_complaints(complaints, form)
    paginator = Paginator(complaints, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "complaints/faculty_complaint_list.html",
        {
            "form": form,
            "page_obj": page_obj,
            "complaints": page_obj.object_list,
        },
    )


admin_complaint_list = faculty_complaint_list


@faculty_required
@require_POST
def faculty_accept_complaint(request, pk):
    complaint = get_object_or_404(_faculty_complaint_queryset(request.user), pk=pk)
    if hasattr(request.user, "faculty"):
        complaint.assigned_faculty = request.user.faculty
    record_status(
        complaint,
        Complaint.STATUS_ASSIGNED,
        changed_by=request.user,
        note="Complaint accepted and assigned to faculty.",
    )
    messages.success(request, "Complaint accepted.")
    return redirect("complaint_detail", pk=complaint.pk)


@faculty_required
@require_POST
def faculty_update_complaint(request, pk):
    complaint = get_object_or_404(_faculty_complaint_queryset(request.user), pk=pk)
    old_status = complaint.status
    post_data = request.POST.copy()
    quick_status = post_data.get("status_action")
    if quick_status in dict(Complaint.STATUS_CHOICES):
        post_data["status"] = quick_status
        if quick_status == Complaint.STATUS_RESOLVED and not post_data.get("admin_note"):
            post_data["admin_note"] = "Complaint marked as resolved by faculty."
    form = StatusUpdateForm(post_data, instance=complaint, user=request.user)
    if form.is_valid():
        updated = form.save(commit=False)
        if not is_admin_user(request.user) and hasattr(request.user, "faculty") and not updated.assigned_faculty:
            updated.assigned_faculty = request.user.faculty
        updated.save()
        note = form.cleaned_data.get("admin_note", "")
        if old_status != updated.status:
            record_status(
                updated,
                updated.status,
                changed_by=request.user,
                note=note,
                previous_status=old_status,
            )
        elif note:
            ComplaintStatusHistory.objects.create(
                complaint=updated,
                status=updated.status,
                changed_by=request.user,
                note=note,
            )
            notify_user(
                updated.student,
                f"New update on {updated.ticket_id}",
                note,
                complaint=updated,
            )
        messages.success(request, "Complaint updated.")
    else:
        messages.error(request, "Could not update complaint. Please review the fields.")
    return redirect("complaint_detail", pk=complaint.pk)


admin_update_complaint = faculty_update_complaint


@faculty_required
def feedback_analytics(request):
    complaints = _faculty_complaint_queryset(request.user)
    feedback = Feedback.objects.filter(complaint__in=complaints).select_related("complaint", "student")
    rating_rows = list(feedback.values("rating").annotate(total=Count("id")).order_by("rating"))
    resolved_yes = feedback.filter(was_resolved=True).count()
    resolved_no = feedback.filter(was_resolved=False).count()
    recent_feedback = feedback[:10]
    average = feedback.aggregate(avg=Avg("rating"))["avg"] or 0

    context = {
        "total_feedback": feedback.count(),
        "average_rating": round(average, 1),
        "resolved_yes": resolved_yes,
        "resolved_no": resolved_no,
        "recent_feedback": recent_feedback,
        "rating_labels": json.dumps([f"{row['rating']} star" for row in rating_rows]),
        "rating_values": json.dumps([row["total"] for row in rating_rows]),
    }
    return render(request, "dashboards/feedback_analytics.html", context)


@faculty_required
def export_complaints_csv(request):
    complaints = _faculty_complaint_queryset(request.user)
    form = ComplaintFilterForm(request.GET or None, include_department=True)
    complaints = _filter_complaints(complaints, form)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="campus_complaints_report.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Ticket ID",
            "Student",
            "Email",
            "Category",
            "Department",
            "Assigned Faculty",
            "Priority",
            "Status",
            "Location",
            "Created At",
            "Resolved At",
            "Feedback Rating",
        ]
    )
    for complaint in complaints:
        writer.writerow(
            [
                complaint.ticket_id,
                complaint.student.get_full_name() or complaint.student.username,
                complaint.student.email,
                complaint.category.name,
                complaint.assigned_department.name if complaint.assigned_department else "",
                complaint.assigned_faculty.user.get_full_name() if complaint.assigned_faculty else "",
                complaint.get_priority_display(),
                complaint.get_status_display(),
                complaint.location,
                complaint.created_at.strftime("%Y-%m-%d %H:%M"),
                complaint.resolved_at.strftime("%Y-%m-%d %H:%M") if complaint.resolved_at else "",
                complaint.feedback.rating if hasattr(complaint, "feedback") else complaint.feedback_rating or "",
            ]
        )
    return response
