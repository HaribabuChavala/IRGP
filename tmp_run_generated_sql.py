import oracledb, json
sql = "SELECT c.region AS region, SUM(so.amount) AS total_revenue FROM report_owner.sales_orders so JOIN report_owner.sales_orders c ON c.customer_id = so.customer_id GROUP BY c.region ORDER BY total_revenue DESC FETCH FIRST 100 ROWS ONLY"
conn = oracledb.connect(user='irgp_reader', password='ReaderPass1', host='irgp-oracle', port=1521, service_name='FREEPDB1')
cur = conn.cursor()
try:
    cur.execute(sql)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description] if cur.description else []
    serial_rows = [[None if v is None else str(v) for v in row] for row in rows]
    print(json.dumps({'sql': sql, 'columns': cols, 'rows': serial_rows}))
finally:
    cur.close()
    conn.close()
