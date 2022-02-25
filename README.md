# Calcul de points FFCK

Attention, ce projet est encore en cours et son utilisation nécessite de se plonger dans le code. La visualisation la plus simple et pertinente des données est disponible [ici](https://classementffck.bubbleapps.io/version-test)

## Introduction

Ce code Python a pour objectif de permettre une estimation de la performance individuelle de l'ensemble des compétiteurs en canoë-kayak slalom présents sur les courses de la fédération française de canoë-kayak.
A partir de ces estimations, il est possible de réaliser des classements des athlètes et de comparer les différentes méthodes de classement et d'estimation de performance individuelle.

## Prérequis

Le code fourni est du code python 3 et nécessite la présence de MongoDB sur la machine hôte.
Afin de pouvoir mettre en place les estimations de performance et calcul de classement à l'aide de ce répo git, il faut respecter les étapes suivantes :
- installer python3 et MongoDB
- installer les librairies nécessaires à l'aide de la commande "pip install -r requirements.txt
- créer la base de données MongoDB en executant le script points_updating.py

## Calcul de classements et de métriques

Une fois la base de données récupérée, il est possible de réaliser des estimations de performance et de calculer des classements à l'aide de point_type_creation.
Les méthodes de classements sont disponibles dans le dossier points_methods.
Il est ensuite possible d'évaluer les méthodes utilisées à l'aide du module data_analysis/analyst.py
Le script run.py permet de lancer une API afin d'accéder aux données de la base de données.

