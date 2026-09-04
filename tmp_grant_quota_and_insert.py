import oracledb
conn = oracledb.connect(user='system', password='SysPassword1', host='irgp-oracle', port=1521, service_name='FREEPDB1')
cur = conn.cursor()
try:
    cur.execute("ALTER USER REPORT_OWNER QUOTA UNLIMITED ON USERS")
    cur.execute("INSERT INTO REPORT_OWNER.SALES_ORDERS (customer_id, amount, region) VALUES ('C3', 300.0, 'US')")
    cur.execute("INSERT INTO REPORT_OWNER.SALES_ORDERS (customer_id, amount, region) VALUES ('C4', 450.75, 'APAC')")
    conn.commit()
    print('quota set and inserted')
except Exception as e:
    print('ERROR', e)
finally:
    cur.close()
    conn.close()
