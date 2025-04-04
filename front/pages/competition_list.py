from datetime import datetime
from urllib.parse import quote, unquote

import pandas as pd
from dash import html, dcc, Input, Output, dash_table

from ..app import app
from ..store import services

COLUMNS_DICT = [
    {
        "name": name,
        "id": id,
        "presentation": "markdown",
    }
    for name, id in [
        ("Nom de la compétition", "competition_name"),
        ("date", "date"),
    ]
]

layout = html.Div(
    [
        html.H1("Liste des compétitions", style={"textAlign": "center"}),
        dcc.Dropdown(
            options=[year for year in range(2000, datetime.now().year + 1)],
            value=datetime.now().year,
            id="competition-list-dropdown",
        ),
        html.H2("Compétitions régionales"),
        dash_table.DataTable(
            data=None,
            columns=COLUMNS_DICT,
            id="competitions-list-table-regional",
            markdown_options={"link_target": "_self"},
        ),
        html.H2("Compétitions nationales 3"),
        dash_table.DataTable(
            data=None,
            columns=COLUMNS_DICT,
            id="competitions-list-table-n3",
            markdown_options={"link_target": "_self"},
        ),
        html.H2("Compétitions nationales 2"),
        dash_table.DataTable(
            data=None,
            columns=COLUMNS_DICT,
            id="competitions-list-table-n2",
            markdown_options={"link_target": "_self"},
        ),
        html.H2("Compétitions nationales 1"),
        dash_table.DataTable(
            data=None,
            columns=COLUMNS_DICT,
            id="competitions-list-table-n1",
            markdown_options={"link_target": "_self"},
        ),
        html.H2("Championnats"),
        dash_table.DataTable(
            data=None,
            columns=COLUMNS_DICT,
            id="competitions-list-table-championnat",
            markdown_options={"link_target": "_self"},
        ),
    ]
)


@app.callback(
    Output("competitions-list-table-regional", "data"),
    Output("competitions-list-table-n3", "data"),
    Output("competitions-list-table-n2", "data"),
    Output("competitions-list-table-n1", "data"),
    Output("competitions-list-table-championnat", "data"),
    [Input("competition-list-dropdown", "value")],
)
def update_output(year):
    year = int(year)
    db_service = services.get_db_service()
    request_res = db_service.get_year_competitions(year)
    return format_competition_list(request_res)
    # Mock data for testing
    # df = pd.DataFrame(
    #     {
    #         "competition_name": [
    #             f"[Competition {i}](/competition/{i})" for i in range(1, 11)
    #         ],
    #         "date": [f"{year}-0{i}-01" for i in range(1, 11)],
    #         "competition_level": [
    #             "Nationale 1",
    #             "Nationale 2",
    #             "Nationale 3",
    #             "Régionale",
    #             "Championnat",
    #         ]
    #         * 2,
    #     }
    # )
    # level_names = [
    #     "Régionale",
    #     "Nationale 3",
    #     "Nationale 2",
    #     "Nationale 1",
    #     "Championnat",
    # ]
    # res = []
    # for level in level_names:
    #     res.append(
    #         df[df["competition_level"] == level][["competition_name", "date"]].to_dict(
    #             "records"
    #         )
    #     )
    # return res


def format_competition_list(request_res):
    """
    Format the competition list from the database response.

    Args:
        request_res (list): List of participations from unique competitions

    Returns:
        list: Formatted list of competitions.
    """
    res = list()
    level_names = [
        "Régional",
        "Nationale 3",
        "Nationale 2",
        "Nationale 1",
        "Championnats de France",
    ]
    for level in level_names:
        res.append(
            [
                {
                    "competition_name": f"[{participation['simplifiedCompetitionName']} {participation['competitionPhase']}](/competition/{quote(participation['competitionName'])})",
                    "date": participation["date"].strftime("%Y-%m-%d"),
                }
                for participation in request_res
                if participation["level"] == level
            ]
        )
    return res
