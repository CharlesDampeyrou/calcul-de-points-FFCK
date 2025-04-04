from dash import html, dcc

layout = html.Div(
    [
        html.H1("Acceuil", style={"textAlign": "center"}),
        html.Div(id="output-page1"),
    ]
)
