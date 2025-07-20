import paho.mqtt.client as mqtt
import uuid

class MQTTClient:
    def __init__(self, broker_address="mqtt.eclipseprojects.io", port=1883, on_message_callback=None, 
                 will_topic=None, will_payload=None, will_retain=True, 
                 client_id=None, clean_session=True):

        self.broker_address = broker_address
        self.port = port
        self.on_message_callback = on_message_callback
        
        if client_id is None:
            client_id = f"python-mqtt-{uuid.uuid4()}"

        self.client = mqtt.Client(client_id=client_id, clean_session=clean_session, 
                                  callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        
        if self.on_message_callback:
            self.client.on_message = self.on_message_callback

        if will_topic and will_payload:
            self.client.will_set(will_topic, payload=will_payload, retain=will_retain, qos=1)
            print(f"Last Will configurado para o tópico '{will_topic}'")

    def connect(self):
        try:
            self.client.connect(self.broker_address, self.port, 60)
            self.client.loop_start()
            print(f"Conectado ao Broker MQTT como '{self.client._client_id.decode()}'!")
            return True
        except Exception as e:
            print(f"Erro ao conectar ao Broker MQTT: {e}")
            return False

    def publish(self, topic, payload, qos=1, retain=False):
        self.client.publish(topic, payload, qos=qos, retain=retain)

    def subscribe(self, topic, qos=1):
        self.client.subscribe(topic, qos=qos)
        print(f"Inscrito no tópico: {topic} com QoS={qos}")
    
    def unsubscribe(self, topic):
        self.client.unsubscribe(topic)
        print(f"Inscrição cancelada para o tópico: {topic}")

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        print("Desconectado do Broker MQTT.")