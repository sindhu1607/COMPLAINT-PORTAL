from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .decorators import can_manage_complaints, is_student_user
from .models import (
    Complaint,
    ComplaintCategory,
    ComplaintComment,
    Department,
    Faculty,
    Feedback,
    Student,
)


class BootstrapFormMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.RadioSelect):
                widget.attrs.setdefault("class", "rating-options")
            elif isinstance(widget, forms.FileInput):
                widget.attrs.setdefault("class", "form-control")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


def split_full_name(full_name):
    parts = full_name.strip().split()
    if not parts:
        return "", ""
    return parts[0], " ".join(parts[1:])


class AccountRegistrationForm(BootstrapFormMixin, forms.Form):
    full_name = forms.CharField(max_length=120)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15, required=False)
    department = forms.ModelChoiceField(queryset=Department.objects.filter(is_active=True), required=True)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords do not match.")
        if password1:
            password_validation.validate_password(password1)
        return cleaned


class StudentRegistrationForm(AccountRegistrationForm):
    roll_number = forms.CharField(max_length=30)
    year = forms.ChoiceField(choices=[("", "Select year")] + Student.YEAR_CHOICES, required=False)

    def clean_roll_number(self):
        roll_number = self.cleaned_data["roll_number"].strip().upper()
        if User.objects.filter(username__iexact=roll_number).exists() or Student.objects.filter(
            roll_number__iexact=roll_number
        ).exists():
            raise ValidationError("An account with this roll number already exists.")
        return roll_number

    def save(self):
        first_name, last_name = split_full_name(self.cleaned_data["full_name"])
        user = User.objects.create_user(
            username=self.cleaned_data["roll_number"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=first_name,
            last_name=last_name,
        )
        Student.objects.create(
            user=user,
            roll_number=self.cleaned_data["roll_number"],
            department=self.cleaned_data.get("department"),
            year=self.cleaned_data.get("year", ""),
            phone=self.cleaned_data.get("phone", ""),
        )
        return user


class FacultyRegistrationForm(AccountRegistrationForm):
    faculty_id = forms.CharField(max_length=30)
    designation = forms.CharField(max_length=80, required=False)

    def clean_faculty_id(self):
        faculty_id = self.cleaned_data["faculty_id"].strip().upper()
        if User.objects.filter(username__iexact=faculty_id).exists() or Faculty.objects.filter(
            faculty_id__iexact=faculty_id
        ).exists():
            raise ValidationError("An account with this faculty ID already exists.")
        return faculty_id

    def save(self):
        first_name, last_name = split_full_name(self.cleaned_data["full_name"])
        user = User.objects.create_user(
            username=self.cleaned_data["faculty_id"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=first_name,
            last_name=last_name,
        )
        Faculty.objects.create(
            user=user,
            faculty_id=self.cleaned_data["faculty_id"],
            department=self.cleaned_data.get("department"),
            phone=self.cleaned_data.get("phone", ""),
            designation=self.cleaned_data.get("designation", ""),
        )
        return user


class RoleAuthenticationForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.CharField(label="ID or email")

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.apply_bootstrap()

    def resolve_username(self, username):
        if "@" in username:
            user = User.objects.filter(email__iexact=username).first()
            if user:
                return user.username
        return username

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username and password:
            self.user_cache = authenticate(self.request, username=self.resolve_username(username), password=password)
            if self.user_cache is None:
                raise ValidationError("Invalid login credentials.", code="invalid_login")
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


class StudentAuthenticationForm(RoleAuthenticationForm):
    username = forms.CharField(label="Roll number or email")

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_student_user(user):
            raise ValidationError("Please use the faculty login page for staff accounts.", code="faculty_login_required")


class FacultyAuthenticationForm(RoleAuthenticationForm):
    username = forms.CharField(label="Faculty ID or email")

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not can_manage_complaints(user):
            raise ValidationError("This account does not have faculty access.", code="not_faculty")


AdminAuthenticationForm = FacultyAuthenticationForm


class UserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class StudentProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Student
        fields = ["roll_number", "department", "year", "phone", "avatar"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.apply_bootstrap()


class FacultyProfileForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Faculty
        fields = ["faculty_id", "department", "designation", "phone", "is_available"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.apply_bootstrap()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]
        return [single_file_clean(data, initial)] if data else []


class ComplaintForm(BootstrapFormMixin, forms.ModelForm):
    attachments = MultipleFileField(required=False, help_text="Upload JPG, PNG, PDF, DOC, or DOCX files up to 5 MB.")

    class Meta:
        model = Complaint
        fields = ["title", "description", "category", "assigned_department", "priority", "location", "attachments"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "location": forms.TextInput(attrs={"placeholder": "Example: Hostel Block B, Room 204"}),
        }
        labels = {
            "assigned_department": "Department",
            "location": "Location of issue",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = ComplaintCategory.objects.filter(is_active=True).select_related(
            "department"
        )
        self.fields["assigned_department"].queryset = Department.objects.filter(is_active=True)
        self.apply_bootstrap()

    def clean_attachments(self):
        files = self.cleaned_data.get("attachments") or []
        allowed_extensions = {"jpg", "jpeg", "png", "webp", "pdf", "doc", "docx"}
        for file in files:
            extension = file.name.rsplit(".", 1)[-1].lower()
            if extension not in allowed_extensions:
                raise ValidationError("Only image, PDF, and Word files are allowed.")
            if file.size > 5 * 1024 * 1024:
                raise ValidationError("Each uploaded file must be under 5 MB.")
        return files


class ComplaintCommentForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ComplaintComment
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": "Write a comment or reply..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()


class ComplaintFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(required=False, label="Search", widget=forms.TextInput(attrs={"placeholder": "Ticket ID, title, or student"}))
    category = forms.ModelChoiceField(
        queryset=ComplaintCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All categories",
    )
    status = forms.ChoiceField(required=False, choices=[("", "All statuses")] + Complaint.STATUS_CHOICES)
    priority = forms.ChoiceField(required=False, choices=[("", "All priorities")] + Complaint.PRIORITY_CHOICES)
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="All departments",
    )

    def __init__(self, *args, include_department=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not include_department:
            self.fields.pop("department")
        self.apply_bootstrap()


class StatusUpdateForm(BootstrapFormMixin, forms.ModelForm):
    admin_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Add a note for the student or workflow history"}),
    )

    class Meta:
        model = Complaint
        fields = ["assigned_department", "assigned_faculty", "status", "admin_note"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_department"].queryset = Department.objects.filter(is_active=True)
        faculty_qs = Faculty.objects.filter(is_available=True).select_related("user", "department")
        if user and hasattr(user, "faculty") and user.faculty.department_id:
            faculty_qs = faculty_qs.filter(department=user.faculty.department)
        self.fields["assigned_faculty"].queryset = faculty_qs
        self.apply_bootstrap()


class FeedbackForm(BootstrapFormMixin, forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
        widget=forms.RadioSelect,
        label="Rate faculty support",
    )

    class Meta:
        model = Feedback
        fields = ["was_resolved", "rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional feedback comment"}),
        }
        labels = {
            "was_resolved": "Was your problem resolved?",
            "comment": "Feedback comment",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
