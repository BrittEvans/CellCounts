import streamlit as st
import polars as pl
from pathlib import Path

import cell_stats
import charts

st.set_page_config(layout="wide")
st.title("Cell Count Stats")
uploaded_file = st.file_uploader("Choose a spreadsheet")
if uploaded_file is not None:
    my_stats = cell_stats.compute_stats(uploaded_file)
    my_output = cell_stats.gen_excel_output(my_stats)
    st.download_button(
        label="Click to Download Full Results!",
        data=my_output.getvalue(),
        file_name=Path(uploaded_file.name).stem + "_results.xlsx",
        mime="application/vnd.ms-excel"
    )
    st.dataframe(
        my_stats.top_output.to_pandas(use_pyarrow_extension_array=True),
        use_container_width=True
    )
    for mouse in my_stats.mice_to_drop:
        st.warning(f"{mouse} has no {my_stats.primary_category}")
    st.header(f"Percent of {my_stats.primary_category} Charts")
    st.plotly_chart(
        charts.primary_percents(my_stats.primary_percents()),
        use_container_width=True
    )
    st.header("All Percent Charts")
    st.plotly_chart(
        charts.primary_percents(my_stats.all_percents()),
        use_container_width=True
    )
#    print(my_stats.dapi_percents())
#    st.plotly_chart(
#        charts.strip_bar(my_stats.dapi_percents().filter(pl.col("Category") == "tdtomato/DAPI" )),
#        #charts.dapi_percents(my_stats),
#        use_container_width=True
#    )
#    st.header("All Percent Charts")
#    print(my_stats.all_percents())
#    st.plotly_chart(
#        charts.strip_bar(my_stats.dapi_percents().filter(pl.col("Category") == "tdtomato/DAPI" )),
#        charts.dapi_percents(my_stats.all_percents()),
#        use_container_width=True
#    )

