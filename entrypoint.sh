#!/bin/sh
echo "entering entrypoint.sh"

# Mise à jour des fichiers CSV
echo "Mise à jour des fichiers de course"
python update_csv_files.py

#mise à jour de la BDD
echo "Mise à jour de la base de données"
python points_updating.py

#lancement du serveur
echo "Lancement du serveur"
uwsgi app.ini
