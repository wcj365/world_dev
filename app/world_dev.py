#!/usr/bin/env python3

from datetime import datetime
import json
import requests
from pyjstat import pyjstat
import pandas as pd
import streamlit as st

from ideal_util.common import ideal_config, ideal_ui, ideal_server

url_topics ="https://api.worldbank.org/v2/en/topic?format=json"
url_indicators = "https://api.worldbank.org/v2/en/topic/{}/indicator?format=json&page={}"
url_indicator = "https://api.worldbank.org/v2/en/indicator/{}?format=json"
url_countries = "https://api.worldbank.org/v2/en/country?format=json&page={}"
url_wdidata = "https://api.worldbank.org/v2/en/country/all/indicator/{}?date={}:{}&format=jsonstat"
#url_wdidata2 = "https://api.worldbank.org/v2/{}/country/all/indicator/{}?source=2"

ABOUT = f"""   
In the era of information and innovation, there is neither a shortage of data nor a shortage of software.
The challenge is the skills and efforts required to combine the two to discover insights and inform decisions. 
An interactive visual environment fills this gap as it is designed for researchers and analysts alike to 
explore data without technical barriers.

**The World Development Explorer (WDX)** is a self-service analytics tool for research and business community. 
It is an interactive and visual environment for exploring [**The World Development Indicators (WDI)**](https://wdi.worldbank.org). 
WDI is the World Bank’s premier compilation of cross-country historical data on development. 
The dataset includes more than 1400 socioeconomic indicators of 200 plus countries over 60 years. 
It is rich in information about a country's economy, environment, society, and healthcare. 

WDX helps global communities improve understanding and inspire collaboration for a better world.
WDX is web-based, cloud-hosted, and free for all to use. Users can visually and interactively 
explore trends and relations and compare countries and regions. 
The beautiful and insightful charts are of publication-quality and can be readily downloaded for use
in blogs, presentations, reports, and papers.

Happy Exploring!
"""

def connect():
    with st.expander("❓ ABOUT"):           
        st.markdown(ABOUT) 
    with st.expander(":sunny: QUERY", expanded=True):     
        api, df = query_ui()
        return api, df

        
def query_ui():

    current_year = datetime.now().year
    df_topics = get_topics()
    df_topics["Topic"] = df_topics["id"] + " - " +  df_topics["value"]
    topic_options = list(df_topics["Topic"])
    indicator_options = []
        
    columns = st.columns(4)
    with columns[0]:  
        year_begin= st.number_input(
            "Year From", 
            min_value=1960, 
            max_value=current_year - 1, 
            value=current_year - 20)
    with columns[1]:
        year_end = st.number_input(
            "Year To", 
            min_value=year_begin, 
            max_value=current_year - 1, 
            value=current_year - 1
        ) 
    with columns[2]:
        df_countries = get_countries()    
        region_options = df_countries["Region"].unique()
        region_options.sort()
        regions = st.multiselect("Regions", region_options, placeholder="All Regions")
    with columns[3]:
        if len(regions) == 0:
            country_options = df_countries["Country"]
        else: 
            country_options = df_countries[df_countries["Region"].isin(regions)]["Country"].unique()
        countries = st.multiselect("Countries", country_options, placeholder="All Countries")
        
        
    def add_field():
        st.session_state.wdi_fields_size += 1
        
        
    if "wdi_fields_size" not in st.session_state:
        st.session_state.wdi_fields_size = 0
        st.session_state.wdi_fields = []
    else:
        col1, col2 = st.columns((1,3))
        with col1:
            st.text("Topic")
        with col2:
            st.text("Indicator")
                        
    indicator_list = []

    for i in range(st.session_state.wdi_fields_size):
                       
        col1, col2 = st.columns((1,3))
        with col1:
             topic = st.selectbox(
                 f"Topic {i}", 
                 topic_options, 
                 index=None, 
                 label_visibility="collapsed")
        with col2:
            if topic != None:
                df_indicators = get_indicators(int(topic.split("-")[0]))    
                df_indicators["Indicator"] = df_indicators["id"] + " - " +  df_indicators["name"]
                indicator_options = list(df_indicators["Indicator"])
                indicators = st.multiselect(
                    f"Indicators {i}", 
                    indicator_options, 
                    label_visibility="collapsed"
                )
                indicator_list = indicator_list + indicators
            else:
                indicators = st.multiselect(f"Indicators {i}", [], label_visibility="collapsed")  
                
    st.button("➕ Add Indicators", on_click=add_field)        
           
    if st.button("Run", type="primary"):
        if len(indicator_list) == 0:
            df = pd.DataFrame()
            api = None
            st.warning("Please select at least one indicator.", icon="⚠️")    
        else:
            if len(countries) != 0:
                _df = df_countries[df_countries["Country"].isin(countries)]
            elif len(regions) != 0:
                _df = df_countries[df_countries["Region"].isin(regions)]  
            else:
                _df = df_countries
                
            indicator_list = list(dict.fromkeys(indicator_list))   # Remove potential duplicates
            indicator_list = [x.split("-")[0].strip() for x in indicator_list]    # use the indicator code
                          
            api, df = get_data(
                indicator_list, 
                year_begin, 
                year_end, 
                _df
            )
            st.info(f"{df.shape[0]} Records were retrieved.", icon="ℹ️") 
    else:
        api = None
        df = pd.DataFrame()

    return api, df


@st.cache_data
def get_topics():
    resp = requests.get(url=url_topics)
    json_resp = json.loads(resp.text)
    df = pd.DataFrame(json_resp[1])
    return df
    

@st.cache_data
def get_indicators(topic_id):   
            
    resp = requests.get(url=url_indicators.format(topic_id, 1))
    json_resp = json.loads(resp.text)
    header = json_resp[0]
    contents = json_resp[1]

    for i in range(2, int(header["pages"]) + 1):
        resp = requests.get(url=url_indicators.format(topic_id, i))
        contents += json.loads(resp.text)[1] 

    _df = pd.DataFrame(contents)
    _df.drop(columns=["unit"], inplace=True)
    _df = _df[_df["name"] != ""]
    _df["source"] = _df["source"].apply(lambda source: source["value"] )
    
    return _df


@st.cache_data
def get_countries():

    resp = requests.get(url=url_countries.format(1))
    json_resp = json.loads(resp.text)
    header = json_resp[0]
    contents = json_resp[1]

    for i in range(2, int(header["pages"]) + 1):
        resp = requests.get(url=url_countries.format(i))
        contents += json.loads(resp.text)[1]

    for content in contents:
        content["region"] = content["region"]["value"]
        content["adminregion"] = content["adminregion"]["value"]
        content["incomeLevel"] = content["incomeLevel"]["value"]
        content["lendingType"] = content["lendingType"]["value"]

    df = pd.DataFrame(contents)
    df = df[df["region"] != ""]
    df = df[df["region"] != "Aggregates"]  
    df.drop(columns=["adminregion"], inplace=True) 
    df.reset_index(drop=True, inplace=True)
    df_countries = df[["id", "name", "region", "incomeLevel", "lendingType"]]
    df_countries.columns = ["Country Code", "Country", "Region", "Income Group", "Lending Type"]
    
    return df_countries.sort_values("Country")



@st.cache_data  
def get_data(indicator_list, year_begin, year_end, df_countries):
   
    df_list = []
    api_list = []
    for indicator in indicator_list:          
        try:
            api = url_wdidata.format(indicator, year_begin, year_end)
            api_list.append(api)
            df =  pyjstat.Dataset.read(api).write('dataframe')
        except Exception as e:
            print(e)
            continue
            
        df["indicator"] = df["Series"] 
        df.drop(columns=["Series"], inplace=True)
        df_list.append(df)
        
    if len(df_list) == 0:
        df = pd.DataFrame()
    else:
        if len(df_list) > 1:
            df = pd.concat(df_list) 
        else:
            df = df_list[0]
         
        
    if not df.empty:
        df = pd.pivot(df, index=["Year", "Country"], columns="indicator",  values="value").reset_index()
        df = df.merge(df_countries, how="inner", on="Country")
    
    return " | ".join(api_list), df
