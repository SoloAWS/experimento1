from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
import redis
import json
import os

app = FastAPI()

redis_host = os.getenv("REDIS_HOST", "reportes-cluster-ro.zrnzc3.ng.0001.use1.cache.amazonaws.com")
redis_port = os.getenv("REDIS_PORT", 6379)
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

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
    return {"status": "OK"}

@app.get("/kpis/{uuid}")
async def get_kpis(uuid: UUID):
    try:
        kpi_json = redis_client.get(str(uuid))
        if not kpi_json:
            raise HTTPException(status_code=404, detail="Reporte no encontrado")
        
        kpi_dict = json.loads(kpi_json)
        
        kpi_dict['fecha_inicio'] = datetime.fromisoformat(kpi_dict['fecha_inicio'])
        kpi_dict['fecha_fin'] = datetime.fromisoformat(kpi_dict['fecha_fin'])
        
        return KPIs(**kpi_dict)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID inválido")
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)