from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.mqtt.client import connect, create_client
from app.mqtt.subscriber import subscribe

mqtt_client = create_client()

@asynccontextmanager
async def lifespan(app: FastAPI):
    connect(mqtt_client)
    subscribe(mqtt_client, topic="signal/#")
    mqtt_client.loop_start()
    yield
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


app = FastAPI(title="Signal Craft Backend", lifespan=lifespan)
app.include_router(health_router)
