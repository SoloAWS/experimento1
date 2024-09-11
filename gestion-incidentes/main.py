from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, timedelta
import random
import uuid

app = FastAPI()

class Incident(BaseModel):
    id: str
    estado: str
    costo: float
    fecha: datetime

@app.get("/healthcheck")
async def healthcheck():
    return {"status": "OK"}

@app.get("/incidents")
async def get_incidents(
    fecha_inicio: datetime = Query(..., description="Fecha de inicio del rango"),
    fecha_fin: datetime = Query(..., description="Fecha de fin del rango")
):
    num_incidents = random.randint(10, 100)
    
    incidents = []
    for _ in range(num_incidents):
        random_date = fecha_inicio + timedelta(
            seconds=random.randint(0, int((fecha_fin - fecha_inicio).total_seconds()))
        )
        
        incident = Incident(
            id=str(uuid.uuid4()),
            estado=random.choice(["abierto", "cerrado"]),
            costo=round(random.uniform(100, 10000), 2),
            fecha=random_date
        )
        incidents.append(incident)
    
    return incidents

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)