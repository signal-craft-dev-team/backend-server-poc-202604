from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.database.database import router as database_router
from app.mqtt.client import connect as mqtt_connect, create_client as mqtt_create_client
from app.mqtt.subscriber import subscribe
from app.database.client import connect as db_connect, create_connector, disconnect as db_disconnect

mqtt_client = mqtt_create_client()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # MQTT
    mqtt_connect(mqtt_client)
    subscribe(mqtt_client, topic="signalcraft/#")
    mqtt_client.loop_start()

    # DB — lifespan 안에서 생성해야 이벤트 루프 일치
    db_connector = await create_connector()
    db_connect(db_connector)

    yield

    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    await db_disconnect(db_connector)


app = FastAPI(title="Signal Craft Backend", lifespan=lifespan)
app.include_router(health_router)
app.include_router(database_router)
app.include_router(edge_server_router)
