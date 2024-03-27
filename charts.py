import plotly.express as px
import plotly.graph_objects as go

import cell_stats


def dapi_percents(my_stats: cell_stats.CellStats, n_cols: int = 4) -> go.Figure:
    labels_melted = my_stats.mouse_labels.transpose(
        include_header=True, header_name="mouse", column_names=" "
    )

    dapi_percents = my_stats.top_as_percent.melt(
        id_vars="Category", value_name="percent", variable_name="mouse"
    ).join(labels_melted, on="mouse")

    n_rows = dapi_percents["Category"].n_unique() // n_cols + 1

    fig = px.box(
        dapi_percents,
        y="percent",
        color="Genotype",
        facet_col="Category",
        x="Gender",
        facet_col_wrap=n_cols,
        points="all",
        facet_col_spacing=0.05,
    )
    fig.update_yaxes(
        title="",
        tickformat=".0%",
        matches=None,
        showticklabels=True,
        rangemode="tozero",
    )
    fig.update_layout(height=n_rows * 300)
    fig.update_traces(boxmean="sd", pointpos=0, fillcolor="rgba(0,0,0,0)")
    return fig
