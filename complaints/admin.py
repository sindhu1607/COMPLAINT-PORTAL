from django.contrib import admin

from .models import (
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintComment,
    ComplaintStatusHistory,
    Department,
    Faculty,
    Feedback,
    Notification,
    Student,
)
from .services import record_status


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("user", "roll_number", "department", "year", "phone")
    search_fields = ("user__username", "user__email", "roll_number", "department__name")
    list_filter = ("department", "year")


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("user", "faculty_id", "department", "designation", "is_available")
    search_fields = ("user__username", "user__email", "faculty_id", "department__name")
    list_filter = ("department", "is_available")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "email", "is_active")
    search_fields = ("name", "code", "email")
    list_filter = ("is_active",)


@admin.register(ComplaintCategory)
class ComplaintCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "department", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "department__name")
    list_filter = ("department", "is_active")


class ComplaintAttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0


class ComplaintCommentInline(admin.TabularInline):
    model = ComplaintComment
    extra = 0
    readonly_fields = ("created_at",)


class ComplaintStatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_id",
        "title",
        "student",
        "category",
        "assigned_department",
        "assigned_faculty",
        "priority",
        "status",
        "created_at",
    )
    list_filter = ("status", "priority", "category", "assigned_department", "assigned_faculty", "created_at")
    search_fields = ("ticket_id", "title", "student__username", "student__email", "location")
    readonly_fields = ("ticket_id", "created_at", "updated_at", "accepted_at", "resolved_at", "closed_at", "reopened_at")
    inlines = [ComplaintAttachmentInline, ComplaintCommentInline, ComplaintStatusHistoryInline]

    def save_model(self, request, obj, form, change):
        old_status = None
        if change and obj.pk:
            old_status = Complaint.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if change and old_status and old_status != obj.status:
            record_status(
                obj,
                obj.status,
                changed_by=request.user,
                note="Updated from Django admin.",
                previous_status=old_status,
            )


@admin.register(ComplaintAttachment)
class ComplaintAttachmentAdmin(admin.ModelAdmin):
    list_display = ("complaint", "uploaded_by", "uploaded_at")
    search_fields = ("complaint__ticket_id", "uploaded_by__username")


@admin.register(ComplaintComment)
class ComplaintCommentAdmin(admin.ModelAdmin):
    list_display = ("complaint", "user", "is_faculty_reply", "created_at")
    search_fields = ("complaint__ticket_id", "user__username", "message")
    list_filter = ("is_faculty_reply",)


@admin.register(ComplaintStatusHistory)
class ComplaintStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("complaint", "status", "changed_by", "created_at")
    search_fields = ("complaint__ticket_id", "note")
    list_filter = ("status",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "complaint", "is_read", "created_at")
    search_fields = ("title", "message", "user__username")
    list_filter = ("is_read",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("complaint", "student", "was_resolved", "rating", "created_at")
    search_fields = ("complaint__ticket_id", "student__username", "comment")
    list_filter = ("was_resolved", "rating", "created_at")
