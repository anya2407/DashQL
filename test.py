from tools.sqltools import run_sql
import tools.sqltools as sqltools
from tools.chart_tool import generate_chart
import tools.chart_tool as chart_tool

result_text = run_sql.invoke({"query": "SELECT Country, COUNT(*) as OrderCount FROM Orders JOIN Customers ON Orders.CustomerID = Customers.CustomerID GROUP BY Country"})
print("run_sql text output:\n", result_text)
print("\nStashed DataFrame:\n", sqltools.last_query_result)

chart_result = generate_chart.invoke({"chart_type": "bar", "x_column": "Country", "y_column": "OrderCount"})
print("\ngenerate_chart output:", chart_result)

print("\nNumber of charts stashed:", len(chart_tool.generated_charts))

if chart_tool.generated_charts:
    chart_tool.generated_charts[0].show()