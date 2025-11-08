#upgrade pip
pip install --upgrade pip

#crian env
python -m pip install virtualenv
python -m venv .venv

#entrar no env
source .venv/bin/activate

#instalar requirements
pip install -r requirements.txt

# to create general db of django app
python manage.py migrate

# collect static files
python manage.py collectstatic

# RUNSERVER
python manage.py runserver

# to create user
#python manage.py startapp users
 