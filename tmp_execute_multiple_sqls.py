import oracledb, json, sys
sqls=[
"SELECT c.region AS region, SUM(so.amount) AS total_revenue FROM report_owner.sales_orders so JOIN report_owner.sales_orders c ON c.customer_id = so.customer_id GROUP BY c.region ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY",
"SELECT c.region AS region, SUM(so.amount) AS total_revenue FROM report_owner.sales_orders so JOIN report_owner.sales_orders c ON c.customer_id = so.customer_id GROUP BY c.region ORDER BY total_revenue DESC FETCH FIRST 5 ROWS ONLY",
"SELECT COUNT(*) AS customer_count FROM report_owner.sales_orders"
]
conn = oracledb.connect(user='irgp_reader', password='ReaderPass1', host='irgp-oracle', port=1521, service_name='FREEPDB1')
cur = conn.cursor()
out=[]
for s in sqls:
    try:
        cur.execute(s)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        serial_rows = [[None if v is None else str(v) for v in row] for row in rows]
        out.append({'sql':s,'columns':cols,'rows':serial_rows})
    except Exception as e:
        out.append({'sql':s,'error':str(e)})
print(json.dumps(out))
cur.close()
conn.close()
