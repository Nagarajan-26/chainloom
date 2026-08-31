import streamlit as st


@st.cache_resource
def get_connection():
    """
    Return the native Snowflake connection for Streamlit in Snowflake.

    This application runs on the Streamlit container runtime, so we use
    st.connection("snowflake") rather than st.secrets or _snowflake.
    """
    return st.connection("snowflake")


def get_session():
    """
    Return the Snowpark session associated with the native Snowflake
    Streamlit connection.
    """
    return get_connection().session()


def fetch_dataframe(query: str):
    """
    Execute a SQL query and return the result as a pandas DataFrame.
    """
    return get_connection().query(query)