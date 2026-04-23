import logging
from fastapi import APIRouter, HTTPException
from app.mqtt.publish import publish_ctrl_parameters_server
from app.services.update import update_edge_sensor, update_edge_server
import app.models.schemas as schema

router = APIRouter(prefix="/api/v1", tags=["WEB API"])

logger = logging.getLogger(__name__)


@router.post("/update-server-parameters", response_model=schema.UpdateServerParametersResponse)
async def update_server_parameters(req: schema.UpdateServerParametersRequest):
    server = await update_edge_server(
        server_id=req.server_id,
        place_id=req.place_id,
        server_status=req.server_status,
        capture_duration_ms=req.capture_duration_ms,
        timezone=req.timezone,
        installation_machine=req.installation_machine,
        upload_interval_ms=req.upload_interval_ms,
        active_hours_start=req.active_hours_start,
        active_hours_end=req.active_hours_end,
    )

    if server is None:
        raise HTTPException(status_code=404, detail=f"Server '{req.server_id}' not found")

    params = req.model_dump(exclude={"server_id"}, exclude_none=True)
    mqtt_published = False

    if params:
        try:
            await publish_ctrl_parameters_server(req.server_id, params)
            mqtt_published = True
        except Exception as exc:
            logger.error("[API] MQTT publish failed for %s: %s", req.server_id, exc)
            mqtt_published = False

    return schema.UpdateServerParametersResponse(
        status="updated" if params else "no_changes",
        server_id=req.server_id,
        mqtt_published=mqtt_published,
    )


@router.post("/update-sensor-parameters", response_model=schema.UpdateSensorParametersResponse)
async def update_sensor_parameters(req: schema.UpdateSensorParametersRequest):
    sensor = await update_edge_sensor(
        server_id=req.server_id,
        device_name=req.device_name,
        sensor_type=req.sensor_type,
        sensor_position=req.sensor_position,
        installation_machine=req.installation_machine,
    )

    if sensor is None:
        raise HTTPException(
            status_code=404,
            detail=f"Sensor '{req.device_name}' not found on server '{req.server_id}'",
        )

    params = req.model_dump(exclude={"server_id", "device_name"}, exclude_none=True)

    return schema.UpdateSensorParametersResponse(
        status="updated" if params else "no_changes",
        server_id=req.server_id,
        device_name=req.device_name,
    )
