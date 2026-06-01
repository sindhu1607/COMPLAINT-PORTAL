# Campus Complaint Portal

A full-stack Django web application for campus issue reporting and resolution. Students can register, submit complaints with proof, track progress, receive notifications, and submit feedback after resolution. Faculty members can manage department complaints, accept tickets, update workflow status, reply to students, resolve issues, and review feedback analytics.

## Tech Stack

- Python and Django
- SQLite by default, PostgreSQL-ready through environment variables
- Django Authentication with role-based access
- HTML, CSS, JavaScript
- Bootstrap 5 and Bootstrap Icons
- Chart.js for dashboard analytics

## Major Features

- Modern landing page, student login, faculty login, and registration pages
- Separate Student and Faculty profile models
- Role-protected student and faculty dashboards
- Complaint categories, departments, priorities, location, proof uploads, and automatic ticket IDs like `CMP2026-001`
- Workflow statuses: Submitted, Assigned to Faculty, Under Review, In Progress, Resolved, Closed
- Student complaint history, edit/delete before faculty acceptance, reopen after resolution, notifications, and feedback
- Faculty complaint queue with search, filters, student details, attachment previews, comments, status updates, CSV export, and analytics
- In-app notifications with navbar badge
- Feedback model with resolved confirmation, 1-5 rating, comments, and analytics dashboard
- Secure password hashing, CSRF protection, file type validation, file size validation, and login-required access control

## Project Structure

```text
campus complaint portal/
|-- manage.py
|-- requirements.txt
|-- README.md
|-- campus_complaints/
|   |-- settings.py
|   |-- urls.py
|   |-- asgi.py
|   `-- wsgi.py
|-- complaints/
|   |-- admin.py
|   |-- apps.py
|   |-- context_processors.py
|   |-- decorators.py
|   |-- forms.py
|   |-- models.py
|   |-- services.py
|   |-- urls.py
|   |-- views.py
|   `-- migrations/
|-- templates/
|   |-- public_base.html
|   |-- base.html
|   |-- auth/
|   |-- complaints/
|   |-- dashboards/
|   |-- partials/
|   `-- registration/
`-- static/
    |-- css/
    `-- js/
```

## Setup

1. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Apply migrations:

```powershell
python manage.py migrate
```

4. Create an admin account if you want Django admin access:

```powershell
python manage.py createsuperuser
```

5. Run the app:

```powershell
python manage.py runserver
```

6. Open:

```text
http://127.0.0.1:8000/
```

If port `8000` is already used, run another port:

```powershell
python manage.py runserver 127.0.0.1:8010
```

## App URLs

- Landing page: `http://127.0.0.1:8000/`
- Student login: `http://127.0.0.1:8000/login/`
- Student registration: `http://127.0.0.1:8000/register/`
- Faculty login: `http://127.0.0.1:8000/faculty/login/`
- Faculty registration: `http://127.0.0.1:8000/faculty/register/`
- Django admin: `http://127.0.0.1:8000/django-admin/`

## PostgreSQL Configuration

SQLite works out of the box. To use PostgreSQL, install a driver and set environment variables:

```powershell
pip install psycopg[binary]
$env:DB_ENGINE="django.db.backends.postgresql"
$env:DB_NAME="campus_complaints"
$env:DB_USER="postgres"
$env:DB_PASSWORD="your_password"
$env:DB_HOST="localhost"
$env:DB_PORT="5432"
python manage.py migrate
```

## Notes

- Uploaded proof files are stored in `media/complaint_attachments/`.
- Password reset uses Django's console email backend in development.
- Initial departments and complaint categories are inserted by migrations.
- Faculty users can be created from the faculty registration page or managed in Django admin.
