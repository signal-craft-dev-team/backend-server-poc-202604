import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from sqlalchemy import text

from app.api.web_api import router as web_router
from app.db import mongo, sql
from app.mqtt import client as mqtt_client
from app.mqtt.topics import ALL_SUBSCRIBE_TOPICS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    # 1. Cloud SQL 테이블 생성
    await sql.create_tables()
    logger.info("[DB] Cloud SQL tables ready")

    # 2. MongoDB 연결
    mongo.connect()
    logger.info("[DB] MongoDB connected")

    # 3. MQTT 클라이언트 백그라운드 시작
    stop_event = asyncio.Event()
    mqtt_task = asyncio.create_task(mqtt_client.run(stop_event))

    # handlers dispatcher 주입 (핸들러가 구현되기 전까지 no-op)
    try:
        from app.mqtt.handlers import dispatch  # noqa: PLC0415
        mqtt_client.set_dispatcher(dispatch)
        logger.info("[MQTT] Handler dispatcher registered")
    except ImportError:
        logger.warning("[MQTT] handlers.py not found yet — messages will be dropped")

    logger.info("[MQTT] Background task started, subscribing to %d topics", len(ALL_SUBSCRIBE_TOPICS))

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    stop_event.set()
    mqtt_task.cancel()
    try:
        await mqtt_task
    except asyncio.CancelledError:
        pass

    mongo.disconnect()
    await sql.close_engine()
    logger.info("[Shutdown] All connections closed")


app = FastAPI(
    title="Signal Craft Backend",
    version="0.2.0",
    description="Date: 2026/04/15",
    lifespan=lifespan,
)

app.include_router(web_router)


@app.get("/health")
async def health_check() -> JSONResponse:
    """MQTT 및 DB 연결 상태를 반환한다."""
    mqtt_ok = mqtt_client.is_connected()

    # Cloud SQL ping
    try:
        async with sql.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        sql_ok = True
    except Exception:
        sql_ok = False

    # MongoDB ping
    try:
        await mongo.get_db().command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False

    all_ok = mqtt_ok and sql_ok and mongo_ok
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ok" if all_ok else "degraded",
            "mqtt": mqtt_ok,
            "sql": sql_ok,
            "mongodb": mongo_ok,
        },
    )

# 추후 테스트 통과되면 모두 삭제(혹은 주석 처리)예정
@app.get("/mqtt/topic-publish-test", tags=["TEST"])
async def mqtt_topic_publish_test() -> JSONResponse:
    """MQTT 토픽 발행 테스트 엔드포인트"""
    test_topic = "signalcraft/register_server/cloud/test-server-0002"
    test_message = {"message": "Hello MQTT!"}
    await mqtt_client.publish(test_topic, test_message)
    return JSONResponse(content={"status": "published", "topic": test_topic, "message": test_message})

@app.get("/db/mongo-error-test", tags=["TEST"])
async def db_mongo_error_test() -> JSONResponse:
    """MongoDB 에러 테스트 엔드포인트"""
    try:
        # 존재하지 않는 컬렉션에 접근하여 에러 유발
        await mongo.insert_error_log(event="test_error", server_id="test-server-0001", error="This is a test error", attempts=1)
        return JSONResponse(content={"status": "success"})
    except Exception as e:
        return JSONResponse(content={"status": "error logged", "error": str(e)})