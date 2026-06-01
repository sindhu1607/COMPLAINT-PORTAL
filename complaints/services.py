from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Complaint, ComplaintStatusHistory, Notification


def notify_user(user, title, message, complaint=None, send_email=False):
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        complaint=complaint,
    )
    if send_email and user.email:
        send_mail(
            title,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    return notification


def record_status(complaint, status, changed_by=None, note="", previous_status=None):
    previous_status = previous_status or complaint.status
    complaint.status = status
    now = timezone.now()
    if status in [Complaint.STATUS_ASSIGNED, Complaint.STATUS_UNDER_REVIEW, Complaint.STATUS_IN_PROGRESS]:
        complaint.accepted_at = complaint.accepted_at or now
    if status == Complaint.STATUS_RESOLVED:
        complaint.resolved_at = complaint.resolved_at or now
    if status == Complaint.STATUS_CLOSED:
        complaint.closed_at = complaint.closed_at or now
    complaint.save()

    history = ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=status,
        previous_status=previous_status if previous_status != status else "",
        changed_by=changed_by,
        note=note or f"Status changed to {complaint.get_status_display()}.",
    )

    if previous_status != status:
        if status == Complaint.STATUS_RESOLVED:
            message = f"Your complaint regarding {complaint.title} has been resolved."
        elif status == Complaint.STATUS_CLOSED:
            message = f"Your complaint {complaint.ticket_id} has been closed."
        elif status == Complaint.STATUS_ASSIGNED and complaint.assigned_faculty:
            faculty_name = complaint.assigned_faculty.user.get_full_name() or complaint.assigned_faculty.user.username
            message = f"Your complaint has been assigned to {faculty_name}."
        else:
            message = f"Your complaint is now marked as {complaint.get_status_display()}."
        notify_user(
            complaint.student,
            f"{complaint.ticket_id} status updated",
            message,
            complaint=complaint,
        )

    return history


def record_initial_submission(complaint):
    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        status=Complaint.STATUS_SUBMITTED,
        changed_by=complaint.student,
        note="Complaint submitted successfully.",
    )
    notify_user(
        complaint.student,
        f"{complaint.ticket_id} submitted",
        "Your complaint has been submitted and routed to the selected department.",
        complaint=complaint,
    )


def build_workflow_steps(complaint):
    labels = dict(Complaint.WORKFLOW_STATUS_CHOICES)
    statuses = [status for status, _ in Complaint.WORKFLOW_STATUS_CHOICES]
    current_index = statuses.index(complaint.status) if complaint.status in statuses else 0
    completed_statuses = set(complaint.status_history.values_list("status", flat=True))

    steps = []
    for index, status in enumerate(statuses):
        steps.append(
            {
                "status": status,
                "label": labels[status],
                "is_done": status in completed_statuses or index < current_index,
                "is_current": status == complaint.status,
            }
        )
    return steps
