from tools.databricks_tool import run_databricks_query_df

df = run_databricks_query_df("""
SELECT *
FROM gold.fact_sales
LIMIT 5
""")

print(df)