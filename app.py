import streamlit as st
from pathlib import Path

import cell_stats

st.title("Cell Count Stats")
uploaded_file = st.file_uploader("Choose a spreadsheet")
if uploaded_file is not None:
    my_stats = cell_stats.compute_stats(uploaded_file)
    my_output = cell_stats.gen_excel_output(my_stats)
    st.dataframe(
        my_stats.top_output.to_pandas(use_pyarrow_extension_array=True),
        use_container_width=True
    )
    st.download_button(
        label="Click to Download Full Results!",
        data=my_output.getvalue(),
        file_name=Path(uploaded_file.name).stem + "_results.xlsx",
        mime="application/vnd.ms-excel"
    )

