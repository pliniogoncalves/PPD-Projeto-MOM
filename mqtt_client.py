import paho.mqtt.client as mqtt
import time

class MQTTClient:
    def __init__(self, broker_address="broker.hivemq.com", on_message_callback=None, will_topic=None, will_payload=None, will_retain=False):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        self.broker_address = broker_address
        self.client.on_connect = self.on_connect
        self.client.on_message = on_message_callback
        self.is_connected = False
        if will_topic:
            self.client.will_set(will_topic, will_payload, retain=will_retain)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Conectado ao Broker MQTT: {self.broker_address}")
            self.is_connected = True
        else:
            print(f"Falha ao conectar ao MQTT, código: {rc}")
            self.is_connected = False

    def connect(self):
        try:
            self.client.connect(self.broker_address, 1883, 60)
            self.client.loop_start()
            timeout = time.time() + 2
            while not self.is_connected and time.time() < timeout:
                time.sleep(0.1)
            return self.is_connected
        except Exception as e:
            print(f"Erro ao conectar ao Broker MQTT: {e}")
            return False

    def disconnect(self):
        try:
            self.client.loop_stop()
            self.client.disconnect()
            print("Desconectado do Broker MQTT.")
        except Exception: pass

    def publish(self, topic, payload, retain=False):
        self.client.publish(topic, payload, retain=retain)

    def subscribe(self, topic):
        self.client.subscribe(topic)
        print(f"Inscrito no tópico: {topic}")

    def unsubscribe(self, topic):
        self.client.unsubscribe(topic)
        print(f"Inscrição cancelada para o tópico: {topic}")