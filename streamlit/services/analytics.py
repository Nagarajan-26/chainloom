import pandas as pd

from services.snowflake import get_connection


def _fetch_dataframe(query):
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


def fetch_control_tower_summary():
    """
    Return executive KPIs calculated from the underlying
    governed analytical surfaces.

    Fulfillment:
        SUM(FULFILLED_QUANTITY) / SUM(ORDERED_QUANTITY)

    Delivery:
        ON-TIME eligible shipments / DELIVERY-ELIGIBLE shipments

    Production:
        SUM(PRODUCED_QUANTITY) / SUM(PLANNED_QUANTITY)

    These are independent fact calculations. No fact-to-fact
    joins are performed.
    """

    fulfillment_query = """
        SELECT
            SUM(FULFILLED_QUANTITY)
                / NULLIF(SUM(ORDERED_QUANTITY), 0)
                AS FULFILLMENT_RATE
        FROM CHAINLOOM.CURATED.V_CUSTOMER_FULFILLMENT
    """

    delivery_query = """
        SELECT
            COUNT_IF(ON_TIME_FLAG = TRUE)
                / NULLIF(
                    COUNT_IF(DELIVERY_ELIGIBLE_FLAG = TRUE),
                    0
                )
                AS ON_TIME_DELIVERY_RATE
        FROM CHAINLOOM.CURATED.V_SHIPMENT_PERFORMANCE
    """

    production_query = """
        SELECT
            SUM(PRODUCED_QUANTITY)
                / NULLIF(SUM(PLANNED_QUANTITY), 0)
                AS PRODUCTION_ATTAINMENT
        FROM CHAINLOOM.CURATED.V_PRODUCTION_PERFORMANCE
    """

    fulfillment_df = _fetch_dataframe(fulfillment_query)
    delivery_df = _fetch_dataframe(delivery_query)
    production_df = _fetch_dataframe(production_query)

    return {
        "FULFILLMENT_RATE": fulfillment_df.iloc[0]["FULFILLMENT_RATE"],
        "ON_TIME_DELIVERY_RATE": delivery_df.iloc[0][
            "ON_TIME_DELIVERY_RATE"
        ],
        "PRODUCTION_ATTAINMENT": production_df.iloc[0][
            "PRODUCTION_ATTAINMENT"
        ],
    }