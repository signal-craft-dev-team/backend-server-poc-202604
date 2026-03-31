import paho.mqtt.client as mqtt


def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
    topic = message.topic
    payload = message.payload.decode("utf-8")
    print(f"[MQTT] received | topic={topic} payload={payload}")


def subscribe(client: mqtt.Client, topic: str, qos: int = 0) -> None:
    client.subscribe(topic, qos=qos)
    client.on_message = on_message
    print(f"[MQTT] subscribed to {topic}")
