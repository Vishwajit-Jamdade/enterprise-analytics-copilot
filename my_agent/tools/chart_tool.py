from pathlib import Path

import matplotlib.pyplot as plt

from .databricks_tool import run_databricks_query_df

ROOT_DIR = Path(__file__).resolve().parents[2]


def generate_monthly_revenue_chart() -> str:
    """
    Generate monthly revenue trend chart.
    """

    query = """
    SELECT
        DATE_TRUNC('month', order_date) AS month,
        SUM(net_revenue) AS revenue
    FROM gold.fact_sales
    GROUP BY 1
    ORDER BY 1
    """

    df = run_databricks_query_df(query)

    chart_dir = ROOT_DIR / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    chart_path = chart_dir / "monthly_revenue_trend.png"

    plt.figure(figsize=(12, 6))

    plt.plot(df["month"], df["revenue"])

    plt.title("Monthly Revenue Trend")

    plt.xlabel("Month")

    plt.ylabel("Revenue")

    plt.xticks(rotation=45)

    plt.tight_layout()

    plt.savefig(chart_path)

    plt.close()

    return str(chart_path.relative_to(ROOT_DIR))
