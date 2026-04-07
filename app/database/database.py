from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, APIRouter
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.client import get_db
from app.database.models import Customer, Place, EdgeServer, EdgeSensor
from app.database.schemas import (
    CustomerCreate, CustomerRead,
    PlaceCreate, PlaceRead,
    EdgeServerCreate, EdgeServerRead,
    EdgeSensorCreate, EdgeSensorRead,
)

router = APIRouter(prefix="/sql", tags=["sql"])


# ── Health Check ──────────────────────────────────────────

@router.get("/health-check")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB Connection Error: {str(e)}")


# ── Customer ──────────────────────────────────────────────

@router.post("/customers", response_model=CustomerRead)
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db)):
    customer = Customer(**data.model_dump())
    db.add(customer)
    await db.commit()
    await db.refresh(customer)
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerRead)
async def read_customer(customer_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# ── Place ─────────────────────────────────────────────────

@router.post("/places", response_model=PlaceRead)
async def create_place(data: PlaceCreate, db: AsyncSession = Depends(get_db)):
    place = Place(**data.model_dump())
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


@router.get("/places/{place_id}", response_model=PlaceRead)
async def read_place(place_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Place).where(Place.id == place_id))
    place = result.scalar_one_or_none()
    if not place:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


# ── EdgeServer ────────────────────────────────────────────

@router.post("/edge-servers", response_model=EdgeServerRead)
async def create_edge_server(data: EdgeServerCreate, db: AsyncSession = Depends(get_db)):
    now = datetime.now(ZoneInfo(data.timezone))
    server = EdgeServer(**data.model_dump(), created_at=now, updated_at=now)
    db.add(server)
    await db.commit()
    await db.refresh(server)
    return server


@router.get("/edge-servers/{server_id}", response_model=EdgeServerRead)
async def read_edge_server(server_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EdgeServer).where(EdgeServer.server_id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="EdgeServer not found")
    return server

@router.get("/edge-servers/{server_id}/sensors", response_model=list[EdgeSensorRead])
async def list_edge_sensors(server_id: str, db: AsyncSession = Depends(get_db)):
    server = await db.execute(select(EdgeServer).where(EdgeServer.server_id == server_id))
    server = server.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="EdgeServer not found")
    result = await db.execute(select(EdgeSensor).where(EdgeSensor.edge_server_id == server.id))
    return result.scalars().all()


# ── EdgeSensor ────────────────────────────────────────────

@router.post("/edge-sensors", response_model=EdgeSensorRead)
async def create_edge_sensor(data: EdgeSensorCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EdgeServer).where(EdgeServer.server_id == data.server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="EdgeServer not found")
    payload = data.model_dump(exclude={"server_id"})
    sensor = EdgeSensor(**payload, edge_server_id=server.id)
    db.add(sensor)
    await db.commit()
    await db.refresh(sensor)
    return sensor


@router.get("/edge-sensors/{sensor_id}", response_model=EdgeSensorRead)
async def read_edge_sensor(sensor_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EdgeSensor).where(EdgeSensor.id == sensor_id))
    sensor = result.scalar_one_or_none()
    if not sensor:
        raise HTTPException(status_code=404, detail="EdgeSensor not found")
    return sensor