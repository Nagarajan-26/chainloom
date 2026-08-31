import streamlit as st


@st.cache_resource
def get_connection():
    """
    Return the native Snowflake connection for Streamlit in Snowflake.

    The application runs on the Snowflake Streamlit Container Runtime,
    so authentication is provided by the Streamlit Snowflake connection
    rather than st.secrets or a separate username/password connection.
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


def fetch_product_risk_signals():
    """
    Return product-level risk signals from the governed curated view.
    """

    query = """
        SELECT
            PRODUCT_ID,
            PRODUCT_NAME,
            FULFILLMENT_RATE,
            ON_TIME_DELIVERY_RATE,
            PRODUCTION_ATTAINMENT,
            RISK_SIGNAL_COUNT,
            FULFILLMENT_RISK_FLAG,
            DELIVERY_RISK_FLAG,
            PRODUCTION_RISK_FLAG
        FROM CHAINLOOM.CURATED.V_PRODUCT_RISK_SIGNALS
        ORDER BY
            RISK_SIGNAL_COUNT DESC,
            PRODUCTION_ATTAINMENT ASC,
            PRODUCT_NAME
    """

    return fetch_dataframe(query)