from dash import html, dcc, Input, Output
from .app import app
from .pages import competitor as competitor_page
from .pages import ranking as ranking_page
from .pages import competition as competition_page
from .pages import home as home_page
from .pages import competition_list as competition_list_page

header = html.Div(
    [
        html.Nav(
            [
                dcc.Link("Accueil", href="/", className="nav-link"),
                dcc.Link("Classement", href="/ranking", className="nav-link"),
                dcc.Link(
                    "Liste des compétitions",
                    href="/competition_list",
                    className="nav-link",
                ),
            ],
            className="navbar navbar-expand-lg navbar-light bg-light",
        ),
    ],
    className="header",
)

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),  # Pour gérer les changements d'URL
        header,
        html.Div(id="page-content"),  # Conteneur dynamique pour le contenu des pages
    ]
)


# Callback pour mettre à jour le contenu en fonction de l'URL
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/" or pathname is None:
        return home_page.layout
    elif pathname.split("/")[1] == "competitor":
        return competitor_page.layout
    elif pathname.split("/")[1] == "competition_list":
        return competition_list_page.layout
    elif pathname.split("/")[1] == "ranking":
        return ranking_page.layout
    elif pathname.split("/")[1] == "competition":
        return competition_page.layout
    else:
        print(pathname)
        return html.H1("404: Page non trouvée", style={"textAlign": "center"})
