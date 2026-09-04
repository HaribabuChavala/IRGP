import sys
sys.path.insert(0, "/app")
import asyncio, time, json
from ai_sql_agent import sql_agent_service

payload={
    "prompt":"show revenue by region",
    "tenant_id":"tenant1",
    "data_source": {"id":"ds1","name":"test","type":"postgres","database":"db"}
}

async def main():
    t0 = time.time()
    res = await sql_agent_service.generate_sql(prompt=payload["prompt"], data_source=payload["data_source"], tenant_id=payload["tenant_id"]) 
    t1 = time.time()
    print("result:", res)
    print("elapsed:", t1 - t0)

asyncio.run(main())
