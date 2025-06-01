#!/usr/local/bin/env python3

import pandas as pd
import streamlit as st

from ideal_util.common import audit_trail, ideal_config, ideal_ui, ideal_server
from ideal_util import data_explorer
import world_dev as wdi 

APP_URL = "TBD"

st.set_page_config(layout="wide")
st.header("World Development Indicators")

api, df = wdi.connect()
params = {
    "API CAll" : api
}


# Use the session state to keep the df alive so the display works
if df.empty and "ingest_df" in st.session_state: 
    df = st.session_state["ingest_df"]

if not df.empty:  
    
    df_params = audit_trail.parameters(params)
    st.session_state["ingest_df"] = df        
    df_cover = audit_trail.coversheet("IDEAL -> World Dev Indicators", APP_URL)
    
    with st.expander(":sunny: RESULTS", expanded=True):      
        ideal_ui.display_dataframe(df)
        file_name = "WDI"
        ideal_ui.download_as_excel(df_cover, df_params, df, file_name) 

    data_explorer.explore(df, display=False)  
