import io
from dataclasses import dataclass
from itertools import combinations, permutations

import polars as pl
from xlsxwriter import Workbook


def ensure_columns(df, cols, default=None):
    needed = set(cols) - set(df.columns)
    return df.with_columns([pl.lit(default, pl.UInt32).alias(i) for i in needed])


@dataclass
class CellStats:
    # First tab
    top_output: pl.DataFrame
    middle_output: pl.DataFrame
    bottom_output: pl.DataFrame

    # Prism tab
    mouse_labels: pl.DataFrame
    top_as_percent: pl.DataFrame
    mid_as_percent: pl.DataFrame

    # Mice that aren't labeled yet
    mice_to_drop: list[str]

    # Primary category
    primary_category: str

    def primary_percents(self) -> pl.DataFrame:
        labels_melted = self.mouse_labels.transpose(
            include_header=True, header_name="mouse", column_names=" "
        )

        return self.top_as_percent.melt(
            id_vars="Category", value_name="percent", variable_name="mouse"
        ).join(labels_melted, on="mouse")

    def all_percents(self) -> pl.DataFrame:
        labels_melted = self.mouse_labels.transpose(
            include_header=True, header_name="mouse", column_names=" "
        )

        all_percents = self.mid_as_percent.melt(
            id_vars="Category", value_name="percent", variable_name="mouse"
        ).join(labels_melted, on="mouse")

        return all_percents


def compute_stats(input_source) -> CellStats:
    # Load the cell data
    cell_data_raw = pl.read_excel(
        input_source,
        sheet_name="Cell Data",
        read_options={
            "skip_rows": 1,
            "columns": ["Category", "Filename"],
            "dtypes": {"Category": pl.String},
        },
    )

    # Load the categories to a dictionary
    categories = dict(
        pl.read_excel(
            input_source, sheet_name="Categories", read_options={"has_header": False}
        ).rows()
    )
    primary_category = categories[1]

    # Load the groups
    groups = pl.read_excel(input_source, sheet_name="Groups")
    column_order = groups["Mouse"].to_list()

    # make a column for each category
    cats = list(categories.values())
    cell_data = cell_data_raw.with_columns(
        [
            pl.col("Category").str.contains(num).alias(label)
            for num, label in categories.items()
        ]
    )

    # If there aren't any for the primary category, drop those mice
    mice_with_counts = (
        cell_data.group_by("Filename")
        .agg(pl.col(primary_category).sum())
        .filter(pl.col(primary_category) > 0)["Filename"]
    )
    mice_to_drop = [i for i in column_order if i not in mice_with_counts]

    if mice_to_drop:
        cell_data = cell_data.filter(~pl.col("Filename").is_in(mice_to_drop))
        column_order = [i for i in column_order if i not in mice_to_drop]
        groups = groups.filter(~pl.col("Mouse").is_in(mice_to_drop))

    top_output = (
        cell_data.group_by("Filename")
        .agg(pl.col(cats).sum())
        .transpose(include_header=True, header_name="Category", column_names="Filename")
        .pipe(ensure_columns, cols=column_order)
        .fill_null(0)
        .select("Category", *column_order)
    )

    bottom_output = (
        cell_data.group_by("Filename", *cats)
        .len()
        .with_columns(
            pl.concat_str(
                [
                    pl.when(pl.col(i)).then(pl.lit(f"{i}+")).otherwise(pl.lit(""))
                    for i in cats
                ]
            ).alias("Category")
        )
        .pivot(index="Category", columns="Filename", values="len")
        .pipe(ensure_columns, cols=column_order)
        .fill_null(0)
        .select("Category", *column_order)
    )

    # All but 1
    my_keys = [v for k, v in categories.items() if k > 1]
    middle_output = (
        pl.concat(
            [
                cell_data.filter(pl.col(a) | pl.col(b))
                .group_by("Filename", a, b)
                .len()
                .select(
                    "Filename",
                    "len",
                    pl.concat_str(
                        pl.lit(a),
                        pl.col(a).replace({True: "+", False: "-"}),
                        pl.lit(b),
                        pl.col(b).replace({True: "+", False: "-"}),
                    ).alias("Category"),
                )
                for a, b in combinations(my_keys, 2)
            ]
        )
        .pivot(index="Category", columns="Filename", values="len")
        .pipe(ensure_columns, cols=column_order)
        .fill_null(0)
        .select("Category", *column_order)
    )

    # Prism friendly
    mouse_labels = groups.transpose(
        include_header=True, header_name=" ", column_names="Mouse"
    ).select(" ", *column_order)

    # Top as percent
    all_output = pl.concat([top_output, middle_output, bottom_output])
    denom = top_output.row(by_predicate=pl.col("Category") == primary_category)[1:]
    top_as_percent = (
        all_output.filter(pl.col("Category") != primary_category)
        .select(
            pl.concat_str("Category", pl.lit(primary_category), separator="/"),
            *[pl.col(c) / d for c, d in zip(column_order, denom, strict=True)],
        )
        .fill_nan(0)
    )

    # Middle as percent
    mid_as_percent = pl.concat(
        [
            middle_output.filter(
                pl.col("Category").str.contains(f"{a}+", literal=True),
                pl.col("Category").str.contains(f"{b}", literal=True),
            ).select(
                pl.concat_str("Category", pl.lit(a), separator="/"),
                pl.exclude("Category") / pl.exclude("Category").sum(),
            )
            for a, b in permutations(my_keys, 2)
        ]
    ).fill_nan(0)

    return CellStats(
        top_output,
        middle_output,
        bottom_output,
        mouse_labels,
        top_as_percent,
        mid_as_percent,
        mice_to_drop,
        primary_category,
    )


def gen_excel_output(stats: CellStats) -> io.BytesIO:
    output = io.BytesIO()
    with Workbook(output) as wb:
        n_top = stats.top_output.height
        n_middle = stats.middle_output.height
        n_labels = stats.mouse_labels.height

        stats.mouse_labels.write_excel(
            workbook=wb,
            worksheet="Cell Count Summary",
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
            column_formats={" ": {"bold": True}},
        )

        stats.top_output.write_excel(
            workbook=wb,
            worksheet="Cell Count Summary",
            position=(n_labels + 1, 0),
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
        )
        stats.middle_output.write_excel(
            workbook=wb,
            worksheet="Cell Count Summary",
            position=(n_labels + 1 + n_top + 2, 0),
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
        )
        stats.bottom_output.write_excel(
            workbook=wb,
            worksheet="Cell Count Summary",
            position=(n_labels + 1 + n_top + 2 + n_middle + 2, 0),
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
            freeze_panes=(0, 1),
        )
        # prism friendly tab
        n_top_prism = stats.top_as_percent.height
        stats.mouse_labels.write_excel(
            workbook=wb,
            worksheet="Prism Friendly",
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
            column_formats={" ": {"bold": True}},
        )
        stats.top_as_percent.write_excel(
            workbook=wb,
            worksheet="Prism Friendly",
            include_header=False,
            position=(n_labels + 1, 0),
            autofit=True,
            autofilter=False,
            dtype_formats={pl.FLOAT_DTYPES: "0.00%"},
            column_formats={"Category": {"bold": True}},
        )

        stats.mouse_labels.write_excel(
            workbook=wb,
            worksheet="Prism Friendly",
            position=(n_labels + n_top_prism + 2, 0),
            header_format={"bold": True},
            autofit=True,
            autofilter=False,
            column_formats={" ": {"bold": True}},
        )
        stats.mid_as_percent.write_excel(
            workbook=wb,
            worksheet="Prism Friendly",
            include_header=False,
            position=(n_labels * 2 + n_top_prism + 3, 0),
            autofit=True,
            autofilter=False,
            dtype_formats={pl.FLOAT_DTYPES: "0.00%"},
            column_formats={"Category": {"bold": True}},
            freeze_panes=(0, 1),
        )

    return output
