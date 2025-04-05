from datetime import datetime, timedelta
from random import randint
from urllib.parse import quote, unquote

import pandas as pd
from dash import html, dcc, Input, Output
from dash.dash_table import DataTable
from plotly import graph_objects as go

from ..app import app
from ..store import services

layout = html.Div(
    [
        html.H1("Alice C1D", style={"textAlign": "center"}, id="competitor-name"),
        DataTable(
            data=None,
            id="competitor-details",
            columns=[
                {
                    "name": "detail_name",
                    "id": "detail_name",
                    "presentation": "markdown",
                },
                {
                    "name": "detail_value",
                    "id": "detail_value",
                    "presentation": "markdown",
                },
            ],
            markdown_options={"link_target": "_self"},
            style_header={"display": "none"},
        ),
        dcc.Graph(id="competitor-result-graph"),
        html.H2("Résultats"),
        html.Div(id="competitor-result-tables"),
    ]
)


@app.callback(
    Output("competitor-name", "children"),
    # Output("competitor-details", "columns"),
    Output("competitor-details", "data"),
    Output("competitor-result-graph", "figure"),
    Output("competitor-result-tables", "children"),
    Input("url", "pathname"),
)
def update_competitor_page(pathname):
    point_type = "scrapping"
    name, cat = get_competitor_name_cat(pathname)
    name_cat = f"{name} {cat}"
    details = get_competitor_details(name, cat, point_type)
    fig = get_competitor_result_graph(pathname)
    tables = get_competitor_result_tables(pathname)
    return name_cat, details, fig, tables


def get_competitor_name_cat(pathname):
    suffix = pathname.split("/")[-1]
    cat = suffix.split("_")[-1]
    name = unquote(suffix.split("_")[0])
    return name, cat


def get_competitor_details(name, cat, point_type):
    db_service = services.get_db_service()
    request_res = db_service.get_todays_competitor_ranking(name, cat)
    value = request_res.get(point_type).get("moy")
    if value is None:
        value = " "
    rank = request_res.get(point_type).get("rank")
    res = [
        {"detail_name": "Valeur", "detail_value": value},
        {"detail_name": "Place au classement", "detail_value": rank},
        {"detail_name": "Catégorie", "detail_value": f"[{cat}](/ranking/{cat})"},
    ]
    return res


def get_competitor_result_graph(pathname):
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=competition_results["date"],
            y=competition_results["points"],
            mode="markers",
            name="Points",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=competition_results["date"],
            y=competition_results["value"],
            mode="lines",
            name="Valeur",
        )
    )
    return fig


def get_competitor_result_tables(pathname):
    df = competition_results.copy()
    df["competition_name"] = df["competition_name"].apply(
        lambda x: f"[{x}](/competition/{x.split()[1]})"
    )
    table = DataTable(
        data=df.to_dict("records"),
        columns=[
            {
                "name": "Competition",
                "id": "competition_name",
                "presentation": "markdown",
            },
            {"name": "Date", "id": "date"},
            {"name": "Points", "id": "points"},
            {"name": "Valeur", "id": "value"},
        ],
        markdown_options={"link_target": "_self"},
    )
    return [table]


def get_competition_results():
    df = pd.DataFrame()
    df["competition_name"] = [f"Competition {i}" for i in range(1, 20)]
    df["date"] = [
        (datetime.now() - i * timedelta(days=15)).date().isoformat()
        for i in range(1, 20)
    ]
    df["points"] = [max(0, 200 + randint(-50, 50)) for i in range(1, 20)]
    df["value"] = df["points"].rolling(5, min_periods=1).mean()
    return df


competition_results = get_competition_results()
