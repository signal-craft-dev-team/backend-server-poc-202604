"""MQTT topic helpers."""

_CONTROL_BASE = "signalcraft/control_server"

def control_topic(server_id: str) -> str:
    """Topic the backend publishes control commands to."""
    return f"{_CONTROL_BASE}/{server_id}"


def control_ack_topic(server_id: str) -> str:
    """Topic the edge server publishes ACK responses to."""
    return f"{_CONTROL_BASE}/{server_id}/ack"
