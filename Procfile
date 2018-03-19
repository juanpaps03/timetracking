web: pip install -r local.txt
web: python manage.py migrate sites
web: python manage.py migrate
web: gunicorn config.wsgi:application

