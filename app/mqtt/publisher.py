import paho.mqtt.client as mqtt


def publish(client: mqtt.Client, topic: str, payload: str, qos: int = 0) -> None:
    result = client.publish(topic, payload, qos=qos)
    result.wait_for_publish()
    print(f"[MQTT] published | topic={topic} payload={payload}")
