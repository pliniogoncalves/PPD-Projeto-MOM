import paho.mqtt.client as mqtt
import uuid

class MQTTClient:
    """
    Uma classe wrapper para simplificar o uso do Paho-MQTT.
    Gerencia a conexão, publicação e recebimento de mensagens.
    """
    def __init__(self, broker_address="mqtt.eclipseprojects.io", port=1883, on_message_callback=None):
        """
        Inicializa o cliente MQTT.

        Args:
            broker_address (str): O endereço do broker MQTT.
            port (int): A porta do broker MQTT.
            on_message_callback (function): A função a ser chamada quando uma mensagem é recebida.
                                           Esta função deve aceitar os argumentos: client, userdata, message.
        """
        self.broker_address = broker_address
        self.port = port
        self.on_message_callback = on_message_callback
        
        # Gera um ID de cliente único para evitar conflitos de conexão
        client_id = f"python-mqtt-{uuid.uuid4()}"
        self.client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        
        # Define o callback de mensagem
        if self.on_message_callback:
            self.client.on_message = self.on_message_callback

    def connect(self):
        """
        Conecta-se ao broker MQTT e inicia o loop de rede em uma thread separada.
        """
        try:
            self.client.connect(self.broker_address, self.port, 60)
            # loop_start() inicia uma thread para processar o tráfego de rede,
            # o que permite que a GUI continue responsiva.
            self.client.loop_start()
            print("Conectado ao Broker MQTT com sucesso!")
        except Exception as e:
            print(f"Erro ao conectar ao Broker MQTT: {e}")

    def publish(self, topic, payload, retain=False):
        """
        Publica uma mensagem em um tópico MQTT.

        Args:
            topic (str): O tópico para o qual publicar.
            payload (str): A mensagem a ser enviada.
            retain (bool): Se a mensagem deve ser retida pelo broker.
        """
        result = self.client.publish(topic, payload, retain=retain)
        # status = 0 significa que a publicação foi enfileirada com sucesso.
        if result[0] == 0:
            # print(f"Mensagem enviada para o tópico '{topic}'")
            pass
        else:
            print(f"Falha ao enviar mensagem para o tópico '{topic}'")

    def subscribe(self, topic):
        """
        Inscreve-se em um tópico MQTT.

        Args:
            topic (str): O tópico no qual se inscrever.
        """
        try:
            self.client.subscribe(topic)
            print(f"Inscrito no tópico: {topic}")
        except Exception as e:
            print(f"Erro ao se inscrever no tópico {topic}: {e}")

    def disconnect(self):
        """
        Para o loop de rede e se desconecta do broker.
        """
        self.client.loop_stop()
        self.client.disconnect()
        print("Desconectado do Broker MQTT.")