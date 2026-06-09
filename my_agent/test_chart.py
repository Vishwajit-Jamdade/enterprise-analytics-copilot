from tools.databricks_tool import run_databricks_query_df
from tools.chart_tool import create_line_chart


query = """
SELECT
DATE_TRUNC('month', order_date) AS month,
SUM(net_revenue) AS revenue
FROM gold.fact_sales
GROUP BY 1
ORDER BY 1
"""

df = run_databricks_query_df(query)

chart_path = create_line_chart(
    df,
    "month",
    "revenue",
    "Monthly Revenue Trend"
)

print(chart_path)