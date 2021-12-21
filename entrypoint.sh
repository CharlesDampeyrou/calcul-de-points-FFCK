#!/bin/sh
echo "entering entrypoint.sh"

#mise à jour de la BDD
python points_updating.py

#lancement du serveur
uwsgi app.ini
