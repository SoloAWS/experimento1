from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import redis
import json
import os
import asyncio
from redis.exceptions import RedisError

app = FastAPI()

redis_host = os.getenv("REDIS_HOST", "reportes-cluster-ro.zrnzc3.ng.0001.use1.cache.amazonaws.com")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    socket_timeout=1.5,
    socket_connect_timeout=1.5,
    health_check_interval=30
)

class KPIs(BaseModel):
    uuid: str
    total_incidentes: int
    total_incidentes_abiertos: int
    total_incidentes_cerrados: int
    costos: float
    fecha_inicio: datetime
    fecha_fin: datetime

@app.get("/healthcheck")
async def healthcheck():
    try:
        if redis_client.ping():
            return {"status": "OK", "redis": "Connected"}
        else:
            return {"status": "Degraded", "redis": "Not responding"}
    except RedisError:
        return {"status": "Degraded", "redis": "Connection Error"}

async def get_from_redis(key):
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(redis_client.get, key),
            timeout=1.5
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible")
    except RedisError:
        raise HTTPException(status_code=503, detail="Error de conexión a Redis")

@app.get("/kpis/{uuid}")
async def get_kpis(uuid: UUID):
    try:
        kpi_json = await get_from_redis(str(uuid))
        if not kpi_json:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        kpi_dict = json.loads(kpi_json)
        
        kpi_dict['fecha_inicio'] = datetime.fromisoformat(kpi_dict['fecha_inicio'])
        kpi_dict['fecha_fin'] = datetime.fromisoformat(kpi_dict['fecha_fin'])
        
        return KPIs(**kpi_dict)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID inválido")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)