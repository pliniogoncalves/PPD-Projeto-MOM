import pika
import threading

class RabbitMQClient:
    """
    Uma classe wrapper para simplificar o uso do Pika com RabbitMQ.
    Gerencia conexão, canal, publicação e consumo em uma thread separada.
    """
    def __init__(self, host='localhost'):
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(host))
            self.channel = self.connection.channel()
            print("Conectado ao RabbitMQ com sucesso!")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Erro: Não foi possível conectar ao RabbitMQ em '{host}'.")
            print("Verifique se o servidor RabbitMQ está rodando.")
            raise e

    def declare_exchange(self, exchange_name, exchange_type='fanout'):
        """Declara um exchange (para tópicos)."""
        self.channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type)

    def delete_exchange(self, exchange_name):
        """Deleta um exchange."""
        self.channel.exchange_delete(exchange=exchange_name)

    def declare_queue(self, queue_name):
        """Declara uma fila durável (para usuários)."""
        self.channel.queue_declare(queue=queue_name, durable=True)

    def delete_queue(self, queue_name):
        """Deleta uma fila."""
        self.channel.queue_delete(queue=queue_name)
    
    def get_message_count(self, queue_name):
        """Verifica a quantidade de mensagens em uma fila."""
        try:
            queue_info = self.channel.queue_declare(queue=queue_name, passive=True, durable=True)
            return queue_info.method.message_count
        except Exception:
            return 0

    def publish_to_queue(self, queue_name, message):
        """Publica uma mensagem diretamente para uma fila."""
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2) # Torna a mensagem persistente
        )

    def publish_to_exchange(self, exchange_name, message):
        """Publica uma mensagem para um exchange (tópico)."""
        self.channel.basic_publish(exchange=exchange_name, routing_key='', body=message)

    def start_consuming_from_queue(self, queue_name, callback):
        """Inicia o consumo de uma fila em uma nova thread."""
        def consumer_thread():
            conn = pika.BlockingConnection(pika.ConnectionParameters(self.connection.params.host))
            ch = conn.channel()
            ch.queue_declare(queue=queue_name, durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            try:
                ch.start_consuming()
            except (pika.exceptions.ConnectionClosedByBroker, pika.exceptions.StreamLostError):
                print("Conexão fechada pelo broker, thread de consumo encerrada.")
            finally:
                if conn.is_open:
                    conn.close()

        thread = threading.Thread(target=consumer_thread, daemon=True)
        thread.start()
        print(f"Consumidor iniciado para a fila '{queue_name}' em uma nova thread.")

    def start_consuming_from_exchange(self, exchange_name, callback):
        """Inicia o consumo de um exchange em uma nova thread."""
        def consumer_thread():
            conn = pika.BlockingConnection(pika.ConnectionParameters(self.connection.params.host))
            ch = conn.channel()
            ch.exchange_declare(exchange=exchange_name, exchange_type='fanout')
            result = ch.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue
            ch.queue_bind(exchange=exchange_name, queue=queue_name)
            ch.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
            try:
                ch.start_consuming()
            except (pika.exceptions.ConnectionClosedByBroker, pika.exceptions.StreamLostError):
                print("Conexão fechada pelo broker, thread de consumo encerrada.")
            finally:
                if conn.is_open:
                    conn.close()

        thread = threading.Thread(target=consumer_thread, daemon=True)
        thread.start()
        print(f"Consumidor iniciado para o exchange '{exchange_name}' em uma nova thread.")

    def close(self):
        """Fecha a conexão."""
        if self.connection and self.connection.is_open:
            self.connection.close()
            print("Conexão com RabbitMQ fechada.")