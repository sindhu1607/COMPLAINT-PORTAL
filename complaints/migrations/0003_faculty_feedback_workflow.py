import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def copy_legacy_feedback(apps, schema_editor):
    Complaint = apps.get_model("complaints", "Complaint")
    Feedback = apps.get_model("complaints", "Feedback")
    for complaint in Complaint.objects.exclude(feedback_rating__isnull=True):
        Feedback.objects.update_or_create(
            complaint=complaint,
            defaults={
                "student_id": complaint.student_id,
                "was_resolved": True,
                "rating": complaint.feedback_rating,
                "comment": complaint.feedback_comment,
            },
        )


def seed_requested_categories(apps, schema_editor):
    Department = apps.get_model("complaints", "Department")
    ComplaintCategory = apps.get_model("complaints", "ComplaintCategory")

    departments = {
        "Academic Facilities": ("Academic Facilities", "ACAD-FAC"),
        "Student Housing": ("Student Housing", "HOSTEL"),
        "Laboratory Services": ("Laboratory Services", "LAB"),
        "IT Services": ("IT Services", "IT"),
        "Maintenance": ("Maintenance", "MAINT"),
        "Transport": ("Transport", "TRANS"),
        "Housekeeping": ("Housekeeping", "HOUSE"),
        "Academic Affairs": ("Academic Affairs", "ACADEMICS"),
        "Security": ("Campus Security", "SECURITY"),
        "Student Support": ("Student Support", "SUPPORT"),
    }
    department_objects = {}
    for key, (name, code) in departments.items():
        department, _ = Department.objects.update_or_create(
            code=code,
            defaults={"name": name, "email": f"{code.lower().replace('-', '')}@campus.local", "is_active": True},
        )
        department_objects[key] = department

    categories = [
        ("Classroom Issues", "Academic Facilities"),
        ("Hostel Problems", "Student Housing"),
        ("Lab Equipment Issues", "Laboratory Services"),
        ("WiFi/Internet Problems", "IT Services"),
        ("Electricity Issues", "Maintenance"),
        ("Water Problems", "Maintenance"),
        ("Transport/Bus Issues", "Transport"),
        ("Cleanliness & Hygiene", "Housekeeping"),
        ("Faculty Related Issues", "Academic Affairs"),
        ("Security Problems", "Security"),
        ("Other", "Student Support"),
    ]
    for name, department_key in categories:
        ComplaintCategory.objects.update_or_create(
            name=name,
            defaults={
                "slug": name.lower().replace("/", "-").replace("&", "and").replace(" ", "-"),
                "department": department_objects[department_key],
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("complaints", "0002_seed_initial_data"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="StudentProfile",
            new_name="Student",
        ),
        migrations.RenameModel(
            old_name="StatusTimeline",
            new_name="ComplaintStatusHistory",
        ),
        migrations.CreateModel(
            name="Faculty",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("faculty_id", models.CharField(max_length=30, unique=True)),
                ("phone", models.CharField(blank=True, max_length=15)),
                ("designation", models.CharField(blank=True, max_length=80)),
                ("is_available", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="faculty_members",
                        to="complaints.department",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="faculty",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name_plural": "Faculty", "ordering": ["user__first_name", "user__last_name", "faculty_id"]},
        ),
        migrations.RemoveField(
            model_name="student",
            name="course",
        ),
        migrations.RemoveField(
            model_name="student",
            name="role",
        ),
        migrations.AddField(
            model_name="student",
            name="department",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="students",
                to="complaints.department",
            ),
        ),
        migrations.AlterModelOptions(
            name="student",
            options={"ordering": ["user__first_name", "user__last_name", "roll_number"]},
        ),
        migrations.AlterField(
            model_name="student",
            name="avatar",
            field=models.ImageField(blank=True, null=True, upload_to="profiles/students/"),
        ),
        migrations.AlterField(
            model_name="student",
            name="roll_number",
            field=models.CharField(max_length=30, unique=True),
        ),
        migrations.AlterField(
            model_name="student",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="student",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="student",
            name="year",
            field=models.CharField(
                blank=True,
                choices=[
                    ("1", "1st Year"),
                    ("2", "2nd Year"),
                    ("3", "3rd Year"),
                    ("4", "4th Year"),
                    ("pg", "Postgraduate"),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="accepted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="assigned_faculty",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_complaints",
                to="complaints.faculty",
            ),
        ),
        migrations.AddField(
            model_name="complaint",
            name="closed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="complaint",
            name="location",
            field=models.CharField(blank=True, max_length=180),
        ),
        migrations.AddField(
            model_name="complaintcomment",
            name="is_faculty_reply",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="complaintstatushistory",
            name="previous_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("submitted", "Submitted"),
                    ("assigned", "Assigned to Faculty"),
                    ("under_review", "Under Review"),
                    ("in_progress", "In Progress"),
                    ("resolved", "Resolved"),
                    ("closed", "Closed"),
                    ("rejected", "Rejected"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="complaint",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("assigned", "Assigned to Faculty"),
                    ("under_review", "Under Review"),
                    ("in_progress", "In Progress"),
                    ("resolved", "Resolved"),
                    ("closed", "Closed"),
                    ("rejected", "Rejected"),
                ],
                default="submitted",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="complaintstatushistory",
            name="complaint",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="status_history",
                to="complaints.complaint",
            ),
        ),
        migrations.AlterField(
            model_name="complaintstatushistory",
            name="status",
            field=models.CharField(
                choices=[
                    ("submitted", "Submitted"),
                    ("assigned", "Assigned to Faculty"),
                    ("under_review", "Under Review"),
                    ("in_progress", "In Progress"),
                    ("resolved", "Resolved"),
                    ("closed", "Closed"),
                    ("rejected", "Rejected"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterModelOptions(
            name="complaintstatushistory",
            options={"ordering": ["created_at"], "verbose_name_plural": "Complaint status histories"},
        ),
        migrations.CreateModel(
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("was_resolved", models.BooleanField(default=True)),
                (
                    "rating",
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(5),
                        ]
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "complaint",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="complaints.complaint",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="complaint_feedback",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.RunPython(copy_legacy_feedback, migrations.RunPython.noop),
        migrations.RunPython(seed_requested_categories, migrations.RunPython.noop),
    ]
