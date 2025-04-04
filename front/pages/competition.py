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

    tables = list()
    results = pd.DataFrame(
        {
            "competitor_name": [
                "[Alice](/competitor/Alice_K1D)",
                "[Bob](/competitor/Bob_K1H)",
                "[Charlie](/competitor/Charlie_K1H)",
                "[Alice](/competitor/Alice_C1D)",
                "[Bob](/competitor/Bob_C1H)",
                "[Charlie](/competitor/Charlie_C1H)",
                "[Bob Charlie](/competitor/Bob_Charlie_C2H)",
            ],
            "category": ["K1D", "K1H", "K1H", "C1D", "C1H", "C1H", "C2H"],
            "result": [100, 91, 90, 110, 94, 95, 111],
            "points": [20, 32, 25, 15, 21, 23, 50],
        }
    )
    for cat in results["category"].unique():
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
                        data=results[results["category"] == cat][
                            ["competitor_name", "result", "points"]
                        ].to_dict("records"),
                        markdown_options={"link_target": "_self"},
                    ),
                ]
            )
        )
    return tables


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
