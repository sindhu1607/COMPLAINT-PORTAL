from django.db import migrations
from django.utils.text import slugify


DEPARTMENTS = [
    ("Student Housing", "HOSTEL", "hostel@campus.local"),
    ("Academic Facilities", "ACAD-FAC", "facilities@campus.local"),
    ("Maintenance", "MAINT", "maintenance@campus.local"),
    ("IT Services", "IT", "it@campus.local"),
    ("Transport", "TRANS", "transport@campus.local"),
    ("Laboratory Services", "LAB", "labs@campus.local"),
    ("Academic Affairs", "ACADEMICS", "academics@campus.local"),
    ("Housekeeping", "HOUSE", "housekeeping@campus.local"),
    ("Student Support", "SUPPORT", "support@campus.local"),
]

CATEGORIES = [
    ("Hostel Issues", "Student Housing"),
    ("Classroom Problems", "Academic Facilities"),
    ("Electricity", "Maintenance"),
    ("Water Problems", "Maintenance"),
    ("WiFi/Internet", "IT Services"),
    ("Bus Transport", "Transport"),
    ("Lab Equipment Issues", "Laboratory Services"),
    ("Faculty Related", "Academic Affairs"),
    ("Cleanliness & Hygiene", "Housekeeping"),
    ("Other", "Student Support"),
]


def seed_departments_and_categories(apps, schema_editor):
    Department = apps.get_model("complaints", "Department")
    ComplaintCategory = apps.get_model("complaints", "ComplaintCategory")

    departments = {}
    for name, code, email in DEPARTMENTS:
        department, _ = Department.objects.update_or_create(
            name=name,
            defaults={"code": code, "email": email, "is_active": True},
        )
        departments[name] = department

    for category_name, department_name in CATEGORIES:
        ComplaintCategory.objects.update_or_create(
            name=category_name,
            defaults={
                "slug": slugify(category_name),
                "department": departments[department_name],
                "is_active": True,
            },
        )


def unseed_departments_and_categories(apps, schema_editor):
    ComplaintCategory = apps.get_model("complaints", "ComplaintCategory")
    Department = apps.get_model("complaints", "Department")
    ComplaintCategory.objects.filter(name__in=[name for name, _ in CATEGORIES]).delete()
    Department.objects.filter(name__in=[name for name, _, _ in DEPARTMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("complaints", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_departments_and_categories, unseed_departments_and_categories),
    ]
