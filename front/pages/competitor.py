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
        html.H1(
            "competitorName Category",
            style={"textAlign": "center"},
            id="competitor-name",
        ),
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
    competitor_participations = get_competitor_participations(name, cat)
    fig = get_competitor_result_graph(competitor_participations, point_type)
    tables = get_competitor_result_tables(competitor_participations, point_type)
    return name_cat, details, fig, tables


def get_competitor_name_cat(pathname):
    suffix = pathname.split("/")[-1]
    suffix = unquote(suffix)
    cat = suffix.split("_")[-1]
    name = suffix.split("_")[0]
    return name, cat


def get_competitor_details(name, cat, point_type):
    db_service = services.get_db_service()
    request_res = db_service.get_todays_competitor_ranking(name, cat)
    value = request_res.get(point_type, {"moy": None})["moy"]
    rank = request_res.get(point_type).get("rank")
    res = [
        {"detail_name": "Valeur", "detail_value": value},
        {"detail_name": "Place au classement", "detail_value": rank},
        {"detail_name": "Catégorie", "detail_value": f"[{cat}](/ranking/{cat})"},
    ]
    return res


def get_competitor_participations(name, cat):
    db_service = services.get_db_service()
    return list(db_service.get_competitor_participations(name, cat))


def get_competitor_result_graph(competitor_participations, point_type):
    competition_names = [
        p["simplifiedCompetitionName"] for p in competitor_participations
    ]
    points = [p["points"][point_type] for p in competitor_participations]
    values = [
        p["values"].get(point_type, {"points": None})["points"]
        for p in competitor_participations
    ]
    dates = [p["date"].date() for p in competitor_participations]
    levels = [p["level"] for p in competitor_participations]
    # Create a DataFrame for the results
    competition_results = pd.DataFrame(
        {
            "competition_name": competition_names,
            "date": dates,
            "points": points,
            "value": values,
            "level": levels,
        }
    )
    # Ensure the DataFrame is sorted by date
    competition_results = competition_results.sort_values(by="date", ascending=True)
    fig = go.Figure()
    if competition_results.empty:
        fig.add_annotation(
            text="Aucun résultat disponible",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20),
        )
        return fig
    color_dict = {
        "Championnats de France": "red",
        "Nationale 3": "blue",
        "Nationale 2": "orange",
        "Nationale 1": "purple",
        "Régional": "green",
    }
    fig.add_trace(
        go.Scatter(
            x=competition_results["date"],
            y=competition_results["points"],
            mode="markers",
            name="Points",
            marker_color=competition_results["level"].map(color_dict),
            hovertext=competition_results["competition_name"],
        )
    )
    fig.add_trace(
        go.Scatter(
            x=competition_results["date"],
            y=competition_results["value"],
            mode="lines",
            name="Valeur",
            line=dict(
                color="cyan",
                width=2,
            ),
        )
    )
    return fig


def get_competitor_result_tables(competitor_participations, point_type):
    if len(competitor_participations) == 0:
        return [html.Div("Aucun résultat disponible")]
    simplified_competition_names = [
        p["simplifiedCompetitionName"] for p in competitor_participations
    ]
    competition_names = [p["competitionName"] for p in competitor_participations]
    levels = [p["level"] for p in competitor_participations]
    displayed_competition_names = [
        f"[{simp_name}](/competition/{quote(name)}) {level}"
        for (simp_name, level, name) in zip(
            simplified_competition_names, levels, competition_names
        )
    ]
    dates = [p["date"].date().isoformat() for p in competitor_participations]
    points = [p["points"][point_type] for p in competitor_participations]
    values = [
        p["values"].get(point_type, {"points": None})["points"]
        for p in competitor_participations
    ]
    results_df = pd.DataFrame(
        {
            "competition_name": displayed_competition_names,
            "date": dates,
            "points": points,
            "value": values,
        }
    )
    table = DataTable(
        data=results_df.to_dict("records"),
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
