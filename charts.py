import plotly.express as px
import polars as pl
import plotly.graph_objects as go

import cell_stats


def strip_bar2(
    dapi_percents: pl.DataFrame,
    x="Gender",
    y="percent",
    color="Genotype",
) -> go.Figure:
    by_group = (
        dapi_percents.group_by(x, color, maintain_order=True)
        .agg(
            pl.col(y).mean().alias("mean"),
            (pl.col(y).std(ddof=1) / pl.len().sqrt()).alias("std_err"),
        )
        .fill_null(0)
    )

    color_order = dapi_percents[color].unique(maintain_order=True)
    x_order = dapi_percents[x].unique(maintain_order=True)
    fig = px.bar(
        by_group,
        x=x,
        y="mean",
        color=color,
        barmode="group",
        error_y="std_err",
        category_orders={x: x_order, color: color_order},
    ).update_traces(
        error_y_width=30,
        error_y_thickness=3,
    )
    fig.update_layout(title_x=0.5)

    for my_color in color_order:
        my_df = dapi_percents.filter(pl.col(color) == my_color)
        fig.add_trace(
            go.Box(
                x=my_df[x],
                y=my_df[y],
                color=my_color,
                name=my_color,
                boxpoints="all",
                pointpos=0,
            )
        )
    #    fig.add_trace(
    #        px.box(
    #            dapi_percents,
    #            x=x,
    #            y=y,
    #            color=color,
    #            category_orders={color: color_order, x: x_order},
    #            # stripmode="group",
    #            title="tdtomato/DAPI",
    #        )#.update_traces(
    #         #   showlegend=False,
    #         #   marker_size=10,
    #         #   marker_color="black",
    #         #   pointpos=0,
    #         #   line_color="rgba(0,0,0,0)",
    #         #   fillcolor="rgba(0,0,0,0)",
    #         #   boxpoints="all",
    #        #)#
    #    )
    return fig


#    fig = px.bar(
#        dapi_percents,
#        x=x,
#        y=y,
#        color=color,
#        category_orders={color: color_orders},
#        # stripmode="group",
#        title="tdtomato/DAPI",
#    ).update_traces(
#        showlegend=False,
#        marker_size=10,
#        marker_color="black",
#        pointpos=0,
#        line_color="rgba(0,0,0,0)",
#        fillcolor="rgba(0,0,0,0)",
#        boxpoints="all",
#    )
#    fig.update_yaxes(
#        title="", tickformat=".0%", showticklabels=True, rangemode="tozero"
#    )
#    return fig


def strip_bar(
    dapi_percents: pl.DataFrame,
    x="Gender",
    y="percent",
    color="Genotype",
) -> go.Figure:
    color_orders = dapi_percents[color].unique(maintain_order=True)
    colors = dict(zip(color_orders, px.colors.qualitative.D3))
    fig = px.box(
        dapi_percents,
        x=x,
        y=y,
        color=color,
        category_orders={color: color_orders},
        # stripmode="group",
        title="tdtomato/DAPI",
    ).update_traces(
        showlegend=False,
        marker_size=10,
        marker_color="black",
        pointpos=0,
        line_color="rgba(0,0,0,0)",
        fillcolor="rgba(0,0,0,0)",
        boxpoints="all",
    )
    fig.update_layout(title_x=0.5)
    bars = dapi_percents.group_by(x, color).agg(
        pl.col(y).mean().alias("mean"),
        ((pl.col(y).std(ddof=1)) / pl.len().sqrt()).alias("std_err"),
    )
    for bar_name, bar_color in colors.items():
        bar_df = bars.filter(pl.col(color) == bar_name)
        print(bar_color, bar_df)
        fig.add_trace(
            go.Bar(
                x=bar_df[x],
                y=bar_df["mean"],
                name=bar_name,
                marker_color=bar_color,
                error_y={"type": "data", "array": bar_df["std_err"], "width": 30},
                # fillcolor="rgba(0,0,0,0)"
            )
        )
    fig.update_yaxes(
        title="", tickformat=".0%", showticklabels=True, rangemode="tozero"
    )
    print(fig)
    return fig


def primary_percents(primary: pl.DataFrame, n_cols: int = 4) -> go.Figure:
    n_rows = primary["Category"].n_unique() // n_cols + 1

    fig = px.box(
        primary,
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
    fig.update_traces(boxmean=True, pointpos=0, fillcolor="rgba(0,0,0,0)")
    return fig
