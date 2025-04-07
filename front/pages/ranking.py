from datetime import date, datetime
from urllib.parse import quote

from dash import html, dcc, dash_table, Input, Output, State
import pandas as pd

from ..app import app
from ..store import services

layout = html.Div(
    [
        html.H1("Classement", style={"textAlign": "center"}),
        dcc.Dropdown(
            ["K1D", "K1H", "C1D", "C1H", "C2D", "C2H", "C2M", "all"],
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
        cat = "all"
    db_service = services.get_db_service()
    t = date.today()
    selected_date = datetime(t.year, t.month, t.day)
    point_type = "scrapping"
    request_res = list(
        db_service.get_ranking(
            selected_date,
            point_type,
            cat,
            nb_nat_min=3,
            nb_comp_min=4,
        )
    )
    df = create_ranking_df(request_res)
    # df = pd.DataFrame(
    #     {
    #         "Nom": [
    #             "[Alice](/competitor/alice)",
    #             "[Bob](/competitor/bob)",
    #             "[Charlie](/competitor/charlie)",
    #         ],
    #         "Categorie": [cat] * 3,
    #         "Score": [10, 20, 30],
    #         "Classement": [1, 2, 3],
    #     }
    # )
    return df.to_dict("records"), [
        {"name": i, "id": i, "presentation": "markdown"} for i in df.columns
    ]


def create_ranking_df(request_res):
    categories = [p["_id"]["competitorCategory"] for p in request_res]
    displayed_names = [
        f"[{p['_id']['competitorName']}](/competitor/{quote(p['_id']['competitorName']+'_'+cat)})"
        for p, cat in zip(request_res, categories)
    ]
    values = [p["moy"] for p in request_res]
    rankings = list(range(1, len(request_res) + 1))
    nb_comp = [p["nbComp"] for p in request_res]
    nb_nat = [p["nbNat"] for p in request_res]
    df = pd.DataFrame(
        {
            "Nom": displayed_names,
            "Categorie": categories,
            "Score": values,
            "Classement": rankings,
            "Nombre de compétitions": nb_comp,
            "Nombre de compétitions nationales": nb_nat,
        }
    )
    return df
