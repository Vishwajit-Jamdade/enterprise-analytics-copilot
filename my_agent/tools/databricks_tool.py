import os

import pandas as pd
from databricks import sql

from ..runtime_config import load_agent_env

load_agent_env()


def run_databricks_query(query: str) -> str:
    """
    Execute SQL and return string result.
    """

    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    ) as conn:

        with conn.cursor() as cursor:

            print(f"\nExecuting SQL:\n{query}\n")

            cursor.execute(query)

            rows = cursor.fetchall()

            return str(rows)


def run_databricks_query_df(query: str) -> pd.DataFrame:
    """
    Execute SQL and return DataFrame.
    """

    with sql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN")
    ) as conn:

        with conn.cursor() as cursor:

            print(f"\nExecuting SQL:\n{query}\n")

            cursor.execute(query)

            rows = cursor.fetchall()

            columns = [col[0] for col in cursor.description]

            return pd.DataFrame(rows, columns=columns)
