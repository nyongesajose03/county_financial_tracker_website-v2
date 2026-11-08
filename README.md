# County Financial Tracker

A Django application for exploring county budget allocations, revenue, expenditure,
projects, and public feedback.

## Requirements

- Python 3.12 or newer
- Django 6.0

## Local setup (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DJANGO_SECRET_KEY = (python -c "import secrets; print(secrets.token_urlsafe(50))")
python manage.py migrate
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser. Set `DJANGO_SECRET_KEY` to a
private, persistent value for each environment. For production, also set
`DJANGO_DEBUG=False` and configure `DJANGO_ALLOWED_HOSTS` with the deployment
hostnames.

The SQLite database is created locally and is intentionally excluded from Git.
To load the sample financial records, run:

```powershell
python seed_financial_data.py
```

## Tests

```powershell
python manage.py test
```
