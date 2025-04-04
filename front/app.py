from dash import Dash
import dash_bootstrap_components as dbc  # Optionnel, pour le style

# Initialisation de l'application Dash
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
server = app.server  # Pour déploiement avec Gunicorn ou d'autres serveurs WSGI

# Importer le layout principal de `index.py`
from .index import *  # Assurez-vous que `index.py` contient l'app.layout

if __name__ == "__main__":
    app.run_server(debug=True)  # Lancer l'application
