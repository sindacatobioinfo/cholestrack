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
python manage.py showmigrations
python manage.py makemigrations
python manage.py migrate

# collect static files
python manage.py collectstatic

#create superuser
python manage.py createsuperuser

#if need to add sone info to already existent user
python manage.py makemigrations profile --empty --name create_profiles_for_existing_users

# RUNSERVER
python manage.py runserver

#After changing the site do this to restart the production
sudo systemctl restart nginx
sudo systemctl restart gunicorn 
