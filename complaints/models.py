from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def validate_file_size(file):
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must be under {max_size_mb} MB.")


def complaint_attachment_path(instance, filename):
    ext = Path(filename).suffix
    ticket_id = instance.complaint.ticket_id or "pending"
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return f"complaint_attachments/{ticket_id}/{timestamp}{ext}"


class Department(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Student(models.Model):
    YEAR_CHOICES = [
        ("1", "1st Year"),
        ("2", "2nd Year"),
        ("3", "3rd Year"),
        ("4", "4th Year"),
        ("pg", "Postgraduate"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student")
    roll_number = models.CharField(max_length=30, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    year = models.CharField(max_length=20, choices=YEAR_CHOICES, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    avatar = models.ImageField(upload_to="profiles/students/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name", "roll_number"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.roll_number})"


class Faculty(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="faculty")
    faculty_id = models.CharField(max_length=30, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faculty_members",
    )
    phone = models.CharField(max_length=15, blank=True)
    designation = models.CharField(max_length=80, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Faculty"
        ordering = ["user__first_name", "user__last_name", "faculty_id"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.faculty_id})"


class ComplaintCategory(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="categories",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Complaint categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Complaint(models.Model):
    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_EMERGENCY = "emergency"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "Low"),
        (PRIORITY_MEDIUM, "Medium"),
        (PRIORITY_HIGH, "High"),
        (PRIORITY_EMERGENCY, "Emergency"),
    ]

    STATUS_SUBMITTED = "submitted"
    STATUS_ASSIGNED = "assigned"
    STATUS_UNDER_REVIEW = "under_review"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_RESOLVED = "resolved"
    STATUS_CLOSED = "closed"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ASSIGNED, "Assigned to Faculty"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_REJECTED, "Rejected"),
    ]

    WORKFLOW_STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_ASSIGNED, "Assigned to Faculty"),
        (STATUS_UNDER_REVIEW, "Under Review"),
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_CLOSED, "Closed"),
    ]
    TERMINAL_STATUSES = [STATUS_RESOLVED, STATUS_CLOSED, STATUS_REJECTED]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaints")
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    category = models.ForeignKey(
        ComplaintCategory,
        on_delete=models.PROTECT,
        related_name="complaints",
    )
    assigned_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    assigned_faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    title = models.CharField(max_length=180)
    description = models.TextField()
    location = models.CharField(max_length=180, blank=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    is_reopened = models.BooleanField(default=False)
    reopened_at = models.DateTimeField(blank=True, null=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    feedback_rating = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    feedback_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["ticket_id"], name="complaints__ticket__idx"),
            models.Index(fields=["status", "priority"], name="complaints__status__idx"),
            models.Index(fields=["created_at"], name="complaints__created__idx"),
        ]

    def save(self, *args, **kwargs):
        if self.category and not self.assigned_department:
            self.assigned_department = self.category.department
        if not self.ticket_id:
            self.ticket_id = self.generate_ticket_id()
        now = timezone.now()
        if self.status in [self.STATUS_ASSIGNED, self.STATUS_UNDER_REVIEW, self.STATUS_IN_PROGRESS] and not self.accepted_at:
            self.accepted_at = now
        if self.status == self.STATUS_RESOLVED and not self.resolved_at:
            self.resolved_at = now
        if self.status == self.STATUS_CLOSED and not self.closed_at:
            self.closed_at = now
        if self.status not in [self.STATUS_RESOLVED, self.STATUS_CLOSED]:
            self.resolved_at = None
            self.closed_at = None
        super().save(*args, **kwargs)

    @classmethod
    def generate_ticket_id(cls):
        year = timezone.now().year
        prefix = f"CMP{year}-"
        latest = cls.objects.filter(ticket_id__startswith=prefix).order_by("-ticket_id").first()
        if latest:
            number = int(latest.ticket_id.split("-")[-1]) + 1
        else:
            number = 1
        return f"{prefix}{number:03d}"

    @property
    def is_pending(self):
        return self.status not in self.TERMINAL_STATUSES

    @property
    def can_student_edit(self):
        return self.status == self.STATUS_SUBMITTED and self.assigned_faculty_id is None

    @property
    def requires_feedback(self):
        return self.status in [self.STATUS_RESOLVED, self.STATUS_CLOSED] and not hasattr(self, "feedback")

    def __str__(self):
        return f"{self.ticket_id} - {self.title}"


class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(
        upload_to=complaint_attachment_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=["jpg", "jpeg", "png", "webp", "pdf", "doc", "docx"]
            ),
            validate_file_size,
        ],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    @property
    def is_image(self):
        return Path(self.file.name).suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]

    def __str__(self):
        return f"Attachment for {self.complaint.ticket_id}"


class ComplaintComment(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaint_comments")
    message = models.TextField()
    is_faculty_reply = models.BooleanField(default=False)
    is_admin_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment on {self.complaint.ticket_id} by {self.user.username}"


class ComplaintStatusHistory(models.Model):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=30, choices=Complaint.STATUS_CHOICES)
    previous_status = models.CharField(max_length=30, choices=Complaint.STATUS_CHOICES, blank=True)
    note = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="status_updates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Complaint status histories"

    def __str__(self):
        return f"{self.complaint.ticket_id} moved to {self.get_status_display()}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Feedback(models.Model):
    complaint = models.OneToOneField(Complaint, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="complaint_feedback")
    was_resolved = models.BooleanField(default=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.complaint.feedback_rating = self.rating
        self.complaint.feedback_comment = self.comment
        self.complaint.save(update_fields=["feedback_rating", "feedback_comment", "updated_at"])
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.complaint.ticket_id} feedback - {self.rating}/5"
