import streamlit as st


@st.cache_resource
def get_session():
    return st.connection("snowflake").session()


def _fetch_dataframe(query: str):
    session = get_session()
    return session.sql(query).to_pandas()