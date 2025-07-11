import pika
import threading

class RabbitMQClient:
    def __init__(self, host='localhost'):
        self.host = host
        try:
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.host))
            self.channel = self.connection.channel()
            print("Conectado ao RabbitMQ com sucesso!")
        except pika.exceptions.AMQPConnectionError as e:
            print(f"Erro: Não foi possível conectar ao RabbitMQ em '{host}'.")
            print("Verifique se o servidor RabbitMQ está rodando.")
            raise e
    
    def declare_exchange(self, exchange_name, exchange_type='fanout'):
        self.channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type)

    def delete_exchange(self, exchange_name):
        self.channel.exchange_delete(exchange=exchange_name)

    def declare_queue(self, queue_name):
        self.channel.queue_declare(queue=queue_name, durable=True)

    def delete_queue(self, queue_name):
        self.channel.queue_delete(queue=queue_name)
    
    def get_message_count(self, queue_name):
        try:
            queue_info = self.channel.queue_declare(queue=queue_name, passive=True, durable=True)
            return queue_info.method.message_count
        except Exception:
            return 0

    def publish_to_queue(self, queue_name, message):
        self.channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=message,
            properties=pika.BasicProperties(delivery_mode=2)
        )

    def publish_to_exchange(self, exchange_name, message):
        self.channel.basic_publish(exchange=exchange_name, routing_key='', body=message)

    def start_consuming_from_queue(self, queue_name, callback):
        def consumer_thread():
            try:
                conn = pika.BlockingConnection(pika.ConnectionParameters(self.host))
                ch = conn.channel()
                ch.queue_declare(queue=queue_name, durable=True)
                ch.basic_qos(prefetch_count=1)
                ch.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                ch.start_consuming()
            except (pika.exceptions.ConnectionClosedByBroker, pika.exceptions.StreamLostError, pika.exceptions.ConnectionWrongStateError):
                print("Conexão fechada, thread de consumo da fila encerrada.")
            finally:
                if 'conn' in locals() and conn.is_open:
                    conn.close()

        thread = threading.Thread(target=consumer_thread, daemon=True)
        thread.start()
        print(f"Consumidor iniciado para a fila '{queue_name}' em uma nova thread.")

    def start_consuming_from_exchange(self, exchange_name, callback):
        def consumer_thread():
            try:
                conn = pika.BlockingConnection(pika.ConnectionParameters(self.host))
                ch = conn.channel()
                ch.exchange_declare(exchange=exchange_name, exchange_type='fanout')
                result = ch.queue_declare(queue='', exclusive=True)
                queue_name = result.method.queue
                ch.queue_bind(exchange=exchange_name, queue=queue_name)
                ch.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)
                ch.start_consuming()
            except (pika.exceptions.ConnectionClosedByBroker, pika.exceptions.StreamLostError, pika.exceptions.ConnectionWrongStateError):
                print("Conexão fechada, thread de consumo do exchange encerrada.")
            finally:
                if 'conn' in locals() and conn.is_open:
                    conn.close()

        thread = threading.Thread(target=consumer_thread, daemon=True)
        thread.start()
        print(f"Consumidor iniciado para o exchange '{exchange_name}' em uma nova thread.")

    def close(self):
        """Fecha a conexão de forma segura."""
        if self.connection and self.connection.is_open:
            try:
                self.connection.close()
                print("Conexão com RabbitMQ fechada.")
            except pika.exceptions.StreamLostError:
                print("Conexão com RabbitMQ já havia sido perdida, mas foi encerrada.")