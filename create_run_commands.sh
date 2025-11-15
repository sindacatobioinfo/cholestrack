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
sudo systemctl restart gunicorn 
sudo systemctl restart nginx

#To inject data into the tables (samples and/or files)
python manage.py import_data \
--samples /home/burlo/Downloads/samples_patient.tsv \
--files /home/burlo/Downloads/files_analysisfilelocation.tsv \
--clear #use this only if you want to overwrite the tables

#clear cache smart search
python manage.py load_hpo_data --clear #recreate the database
python manage.py clear_search_cache --all #clear all cache
python manage.py test_gene_search --gene BRCA1 #test gene search