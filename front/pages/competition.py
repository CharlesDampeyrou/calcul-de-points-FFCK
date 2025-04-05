from random import gauss
from urllib.parse import quote, unquote

from dash import html, dcc, Input, Output
from dash.dash_table import DataTable
import pandas as pd

from ..app import app
from ..store import services

layout = html.Div(
    [
        html.H1("Competition", style={"textAlign": "center"}),
        html.Div(id="competition-tables"),
    ]
)


@app.callback(
    Output("competition-tables", "children"),
    Input("url", "pathname"),
    # State("point-type-selector", "value"),
)
def update_competition_tables(pathname):
    point_type = "scrapping"
    competition_name = unquote(pathname.split("/")[-1])
    db_service = services.get_db_service()
    categories = ["K1D", "K1H", "K1H", "C1D", "C1H", "C1H", "C2H"]
    participations = dict()
    for cat in categories:
        participations[cat] = db_service.get_competition_participations(
            competition_name, category=cat, sort_by_score=True
        )
    return create_tables_from_participations(participations, point_type=point_type)


def create_tables_from_participations(participations, point_type):
    tables = list()
    for cat, cat_participations in participations.items():
        cat_participations = list(cat_participations)
        competitor_names = [
            f"[{cat_participation['competitorName']}](/competitor/{quote(cat_participation['competitorName'] + '_' + cat)})"
            for cat_participation in cat_participations
        ]
        categories = [cat] * len(competitor_names)
        scores = [
            cat_participation["score"] for cat_participation in cat_participations
        ]
        points = [
            cat_participation["points"].get(point_type)
            for cat_participation in cat_participations
        ]

        res_df = pd.DataFrame(
            {
                "competitor_name": competitor_names,
                "category": categories,
                "result": scores,
                "points": points,
            }
        )
        tables.append(
            html.Div(
                [
                    html.H2(cat),
                    DataTable(
                        columns=[
                            {
                                "name": "Competitor",
                                "id": "competitor_name",
                                "presentation": "markdown",
                            },
                            {"name": "Result", "id": "result"},
                            {"name": "Points", "id": "points"},
                        ],
                        data=res_df.to_dict("records"),
                        markdown_options={"link_target": "_self"},
                    ),
                ]
            )
        )
    return tables
