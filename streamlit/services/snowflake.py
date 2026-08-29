import streamlit as st
import snowflake.connector


def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["snowflake"]["user"],
        password=st.secrets["snowflake"]["password"],
        account=st.secrets["snowflake"]["account"],
        warehouse=st.secrets["snowflake"]["warehouse"],
        database=st.secrets["snowflake"]["database"],
        schema=st.secrets["snowflake"]["schema"],
        role=st.secrets["snowflake"]["role"],
    )


def fetch_product_risk_signals():
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

    conn = get_connection()

    try:
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            return cursor.fetch_pandas_all()
        finally:
            cursor.close()
    finally:
        conn.close()