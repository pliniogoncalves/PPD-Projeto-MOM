import customtkinter as ctk
from tkinter import messagebox
from rabbitmq_client import RabbitMQClient
from mqtt_client import MQTTClient

UNIQUE_PREFIX = "ppd-plinio-hibrido/"
TOPIC_MGMT_USERS = f"{UNIQUE_PREFIX}sistema/gerenciamento/usuarios"
TOPIC_AUTH_REQUEST = f"{UNIQUE_PREFIX}sistema/auth/request"


class ManagerHibridoApp(ctk.CTk):
    def __init__(self, rabbit_client):
        super().__init__()
        self.rabbit_client = rabbit_client
        self.users = []

        self.title("Gerenciador Híbrido (MQTT + RabbitMQ)")
        self.geometry("400x300")
        
        self.user_entry = ctk.CTkEntry(self, placeholder_text="Nome do usuário")
        self.user_entry.pack(pady=10, padx=20, fill="x")
        add_user_button = ctk.CTkButton(self, text="Adicionar Usuário", command=self.add_user)
        add_user_button.pack(pady=10, padx=20, fill="x")
        self.user_list_box = ctk.CTkTextbox(self, state="disabled")
        self.user_list_box.pack(pady=10, padx=20, fill="both", expand=True)

        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_mqtt_message)
        if not self.mqtt_client.connect():
            self.show_error_and_exit("Não foi possível conectar ao broker MQTT.")
        else:
            self.mqtt_client.subscribe(TOPIC_AUTH_REQUEST)
            print("Gerenciador ouvindo por requisições de autenticação...")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def add_user(self):
        user_name = self.user_entry.get().strip()
        if not user_name or user_name in self.users: return
        
        queue_name = f"queue_{user_name}"
        self.rabbit_client.declare_queue(queue_name)
    
        self.mqtt_client.publish(f"{TOPIC_MGMT_USERS}/{user_name}", "ADD", retain=True)
        
        self.users.append(user_name)
        self.update_user_display()
        self.user_entry.delete(0, ctk.END)
        print(f"Usuário '{user_name}' criado.")

    def update_user_display(self):
        self.user_list_box.configure(state="normal")
        self.user_list_box.delete("1.0", "end")
        self.user_list_box.insert("end", "Usuários nesta Sessão:\n" + "\n".join(self.users))
        self.user_list_box.configure(state="disabled")

    def handle_auth_request(self, payload):
        try:
            user_to_check, response_topic = payload.split(";")
            if user_to_check in self.users:
                self.mqtt_client.publish(response_topic, "VALIDO")
                print(f"AUTH: Login validado para o usuário '{user_to_check}'.")
            else:
                self.mqtt_client.publish(response_topic, "INVALIDO")
                print(f"AUTH: Login negado para o usuário inexistente '{user_to_check}'.")
        except ValueError:
            print("Recebida requisição de auth mal formatada.")

    def on_mqtt_message(self, client, userdata, message):
        if message.topic == TOPIC_AUTH_REQUEST:
            self.handle_auth_request(message.payload.decode())

    def on_closing(self):
        self.rabbit_client.close()
        self.mqtt_client.disconnect()
        self.destroy()
        
    def show_error_and_exit(self, error_message):
        messagebox.showerror("Erro Crítico", error_message)
        self.on_closing()

if __name__ == "__main__":
    try:
        rabbit_client = RabbitMQClient()
        app = ManagerHibridoApp(rabbit_client)
        app.mainloop()
    except Exception as e:
        messagebox.showerror("Erro Crítico", f"Falha ao iniciar o Gerenciador Híbrido.\n{e}")