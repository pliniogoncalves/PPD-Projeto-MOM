import paho.mqtt.client as mqtt
import threading

class MQTTClient:
    def __init__(self, broker_address="mqtt.eclipseprojects.io", on_message_callback=None, will_topic=None, will_payload=None, will_retain=False):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.broker_address = broker_address
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.on_message_callback = on_message_callback
        self.is_connected = False
        if will_topic:
            self.client.will_set(will_topic, will_payload, retain=will_retain)
            print(f"Last Will configurado para o tópico '{will_topic}'")

    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Conectado ao Broker MQTT com sucesso!")
            self.is_connected = True
        else:
            print(f"Falha ao conectar ao MQTT, código de retorno {reason_code}")
            self.is_connected = False

    def on_message(self, client, userdata, msg):
        if self.on_message_callback:
            self.on_message_callback(client, userdata, msg)

    def connect(self):
        try:
            self.client.connect(self.broker_address, 1883, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Erro ao conectar ao Broker MQTT: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """Desconecta de forma segura."""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            print("Desconectado do Broker MQTT.")
        except Exception as e:
            print(f"Erro menor durante a desconexão do MQTT (pode ser ignorado): {e}")

    def publish(self, topic, payload, retain=False):
        self.client.publish(topic, payload, retain=retain)

    def subscribe(self, topic):
        self.client.subscribe(topic)
        print(f"Inscrito no tópico: {topic}")