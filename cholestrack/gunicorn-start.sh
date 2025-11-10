#!/bin/bash
NAME="cholestrack"                                # Name of the application
DJANGODIR=/home/burlo/cholestrack/cholestrack   # Django project directory
SOCKFILE=/home/burlo/cholestrack/deploy_management/run/gunicorn.sock   # we will communicate using this unix socket
USER=burlo                                   # The user to run as
GROUP=burlo                                  # The group to run as
NUM_WORKERS=2                                   # How many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=project.settings       # Which settings file should Django use
DJANGO_WSGI_MODULE=project.wsgi               # WSGI module name
echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $DJANGODIR
source /home/burlo/cholestrack/cholestrack/.venv/bin/activate
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Load environment variables from .env file
if [ -f /home/burlo/cholestrack/cholestrack/.env ]; then
    export $(grep -v '^#' /home/burlo/cholestrack/cholestrack/.env | xargs)
fi

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn
exec gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user $USER \
  --bind=unix:$SOCKFILE
