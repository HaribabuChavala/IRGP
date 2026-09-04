import oracledb
conn = oracledb.connect(user='system', password='SysPassword1', host='irgp-oracle', port=1521, service_name='FREEPDB1')
cur = conn.cursor()
stmts = [
    "CREATE USER REPORT_OWNER IDENTIFIED BY OwnerPass1",
    "GRANT CREATE SESSION TO REPORT_OWNER",
    "GRANT CREATE TABLE TO REPORT_OWNER",
    "CREATE TABLE REPORT_OWNER.SALES_ORDERS (customer_id VARCHAR2(50), amount NUMBER(12,2), region VARCHAR2(50))",
    "INSERT INTO REPORT_OWNER.SALES_ORDERS (customer_id, amount, region) VALUES ('C1', 100.0, 'US')",
    "INSERT INTO REPORT_OWNER.SALES_ORDERS (customer_id, amount, region) VALUES ('C2', 200.5, 'EU')",
    "GRANT SELECT ON REPORT_OWNER.SALES_ORDERS TO IRGP_READER",
]
for s in stmts:
    try:
        cur.execute(s)
    except Exception as e:
        # ignore errors if object exists
        print('WARN', e)
conn.commit()
cur.close()
conn.close()
print('done')
