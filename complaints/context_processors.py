from .decorators import can_manage_complaints, is_student_user


def portal_context(request):
    user = request.user
    unread_notifications_count = 0
    if user.is_authenticated:
        unread_notifications_count = user.notifications.filter(is_read=False).count()
    return {
        "unread_notifications_count": unread_notifications_count,
        "is_student_account": is_student_user(user),
        "is_faculty_account": can_manage_complaints(user),
    }
