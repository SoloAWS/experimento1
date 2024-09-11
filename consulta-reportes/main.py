from fastapi import FastAPI, HTTPException
from uuid import UUID
from pydantic import BaseModel
import random
import uvicorn
from datetime import datetime, timedelta

app = FastAPI()

class KPIs(BaseModel):
    uuid: UUID
    total_incidentes: int
    total_incidentes_abiertos: int
    total_incidentes_cerrados: int
    costos: float
    fecha_inicio: datetime
    fecha_fin: datetime

def generate_random_kpis(uuid: UUID) -> KPIs:
    total_incidentes = random.randint(100, 1000)
    total_incidentes_abiertos = random.randint(0, total_incidentes)
    total_incidentes_cerrados = total_incidentes - total_incidentes_abiertos
    
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=30)  # Asumimos un período de 30 días
    
    return KPIs(
        uuid=uuid,
        total_incidentes=total_incidentes,
        total_incidentes_abiertos=total_incidentes_abiertos,
        total_incidentes_cerrados=total_incidentes_cerrados,
        costos=random.uniform(1000, 10000),
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin
    )

@app.get("/kpis/{uuid}")
async def get_kpis(uuid: UUID):
    try:
        kpis = generate_random_kpis(uuid)
        return kpis
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "OK"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)