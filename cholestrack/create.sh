python -m pip install virtualenv
python -m virtualenv venv

# to create user
python manage.py startapp users
 
# to create general db of django app
python manage.py migrate

# RUNSERVER
python manage.py runserver