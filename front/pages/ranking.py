from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd

from ..app import app

layout = html.Div(
    [
        html.H1("Classement", style={"textAlign": "center"}),
        dcc.Dropdown(
            ["K1D", "K1H", "C1D", "C1H", "C2D", "C2H", "C2M", "scratch"],
            value=None,
            id="ranking-dropdown",
        ),
        dash_table.DataTable(
            data=None, id="ranking-table", markdown_options={"link_target": "_self"}
        ),
    ]
)


@app.callback(
    Output("ranking-table", "data"),
    Output("ranking-table", "columns"),
    Input("ranking-dropdown", "value"),
    State("url", "pathname"),
)
def update_table(cat, pathname):
    if cat is not None:
        pass
    elif len(pathname.split("/")) == 3:
        cat = pathname.split("/")[2]
    else:
        cat = "scratch"
    df = pd.DataFrame(
        {
            "Nom": [
                "[Alice](/competitor/alice)",
                "[Bob](/competitor/bob)",
                "[Charlie](/competitor/charlie)",
            ],
            "Categorie": [cat] * 3,
            "Score": [10, 20, 30],
            "Classement": [1, 2, 3],
        }
    )
    return df.to_dict("records"), [
        {"name": i, "id": i, "presentation": "markdown"} for i in df.columns
    ]
