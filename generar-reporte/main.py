from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uuid
from datetime import datetime
import redis
import json
import os
import httpx
from typing import List
import asyncio
from redis.exceptions import RedisError

app = FastAPI()

redis_host = os.getenv("REDIS_HOST", "reportes-cluster.zrnzc3.ng.0001.use1.cache.amazonaws.com")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True,
    socket_timeout=1.5,
    socket_connect_timeout=1.5,
    health_check_interval=30
)

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://172.31.56.137:8000/incidents")
HTTP_TIMEOUT = 2.0

class DateRange(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime

class Incident(BaseModel):
    id: str
    estado: str
    costo: float
    fecha: datetime

class KPIReport(BaseModel):
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

async def get_incidents(fecha_inicio: datetime, fecha_fin: datetime) -> List[Incident]:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                DATA_SERVICE_URL,
                params={
                    "fecha_inicio": fecha_inicio.isoformat(),
                    "fecha_fin": fecha_fin.isoformat()
                },
                timeout=HTTP_TIMEOUT
            )
            response.raise_for_status()
            return [Incident(**incident) for incident in response.json()]
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Timeout al obtener datos del servicio")
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Error al obtener datos del servicio: {str(e)}")

def calculate_kpis(incidents: List[Incident], fecha_inicio: datetime, fecha_fin: datetime) -> KPIReport:
    total_incidentes = len(incidents)
    total_incidentes_abiertos = sum(1 for inc in incidents if inc.estado == "abierto")
    total_incidentes_cerrados = sum(1 for inc in incidents if inc.estado == "cerrado")
    costos = sum(inc.costo for inc in incidents)

    return KPIReport(
        uuid=str(uuid.uuid4()),
        total_incidentes=total_incidentes,
        total_incidentes_abiertos=total_incidentes_abiertos,
        total_incidentes_cerrados=total_incidentes_cerrados,
        costos=costos,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )

async def save_to_redis(key: str, value: str):
    try:
        await asyncio.wait_for(
            asyncio.to_thread(redis_client.set, key, value),
            timeout=1.5
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Timeout al guardar en Redis")
    except RedisError:
        raise HTTPException(status_code=503, detail="Error de conexión a Redis")

@app.post("/kpis")
async def generate_kpi_report(date_range: DateRange):
    try:
        incidents = await get_incidents(date_range.fecha_inicio, date_range.fecha_fin)

        kpi_report = calculate_kpis(incidents, date_range.fecha_inicio, date_range.fecha_fin)

        kpi_dict = kpi_report.dict()
        
        kpi_dict['fecha_inicio'] = kpi_dict['fecha_inicio'].isoformat()
        kpi_dict['fecha_fin'] = kpi_dict['fecha_fin'].isoformat()
        
        await save_to_redis(kpi_report.uuid, json.dumps(kpi_dict))
        
        return {"message": "Reporte generado y guardado exitosamente", "data": kpi_dict}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)