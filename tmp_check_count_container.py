import oracledb
conn = oracledb.connect(user='irgp_reader', password='ReaderPass1', host='irgp-oracle', port=1521, service_name='FREEPDB1')
cur = conn.cursor()
try:
    cur.execute('SELECT COUNT(*) FROM REPORT_OWNER.SALES_ORDERS')
    print(cur.fetchone())
except Exception as e:
    print('ERROR', e)
finally:
    cur.close()
    conn.close()
