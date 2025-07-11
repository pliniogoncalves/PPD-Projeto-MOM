import customtkinter as ctk
from tkinter import messagebox
import uuid
from rabbitmq_client import RabbitMQClient
from mqtt_client import MQTTClient

UNIQUE_PREFIX = "ppd-plinio-hibrido/"
TOPIC_AUTH_REQUEST = f"{UNIQUE_PREFIX}sistema/auth/request"
TOPIC_AUTH_RESPONSE_BASE = f"{UNIQUE_PREFIX}sistema/auth/response"

class UserHibridoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aplicação de Usuário Híbrida")
        self.geometry("400x250")
        self.user_name = None
        self.auth_client = None
        self.mqtt_client = None
        self.rabbit_client = None
        self.create_login_widgets()

    def create_login_widgets(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(self.login_frame, text="Digite seu nome de usuário:", font=ctk.CTkFont(size=15))
        label.pack(pady=10)
        self.username_entry = ctk.CTkEntry(self.login_frame, width=200)
        self.username_entry.pack(pady=10)
        self.login_button = ctk.CTkButton(self.login_frame, text="Entrar", command=self.start_login_validation)
        self.login_button.pack(pady=20)
        self.status_label = ctk.CTkLabel(self.login_frame, text="")
        self.status_label.pack(pady=(0, 10))
        self.username_entry.bind("<Return>", lambda event: self.start_login_validation())

    def start_login_validation(self):
        self.user_name = self.username_entry.get().strip()
        if not self.user_name:
            self.status_label.configure(text="Nome de usuário não pode ser vazio.", text_color="red")
            return

        self.login_button.configure(state="disabled", text="Validando...")
        self.status_label.configure(text="Conectando para validar...", text_color="gray")
        
        response_id = str(uuid.uuid4())
        self.auth_response_topic = f"{TOPIC_AUTH_RESPONSE_BASE}/{response_id}"
        
        self.auth_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.handle_auth_response)
        
        if self.auth_client.connect():
            self.auth_client.subscribe(self.auth_response_topic)
            payload = f"{self.user_name};{self.auth_response_topic}"
            self.auth_client.publish(TOPIC_AUTH_REQUEST, payload)
            self.status_label.configure(text="Aguardando validação do gerente...")
        else:
            self.status_label.configure(text="Erro de conexão. Tente novamente.", text_color="red")
            self.login_button.configure(state="normal", text="Entrar")

    def handle_auth_response(self, client, userdata, message):
        payload = message.payload.decode()
        self.auth_client.disconnect()

        if payload == "VALIDO":
            self.status_label.configure(text="Usuário válido! Conectando...", text_color="green")
            self.after(500, self.proceed_with_main_login)
        else:
            self.status_label.configure(text="Usuário inválido ou não cadastrado.", text_color="red")
            self.login_button.configure(state="normal", text="Entrar")

    def proceed_with_main_login(self):
        self.login_frame.destroy()
        self.geometry("900x700")
        self.title(f"MOM Híbrido - Usuário: {self.user_name}")
        
        try:
            self.rabbit_client = RabbitMQClient()
            print("Conexão com RabbitMQ estabelecida para mensagens offline.")

            will_payload = f"{self.user_name}:OFFLINE"
            TOPIC_PRESENCE = f"{UNIQUE_PREFIX}sistema/presenca"
            self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", will_topic=TOPIC_PRESENCE, will_payload=will_payload)
            self.mqtt_client.connect()
            print("Conexão com MQTT estabelecida para presença e tópicos.")
            
            self.setup_main_ui_stub()

        except Exception as e:
            messagebox.showerror("Erro de Conexão Híbrida", f"Falha ao conectar a um dos serviços: {e}")
            self.destroy()
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_main_ui_stub(self):
        label = ctk.CTkLabel(self, text=f"Bem-vindo, {self.user_name}!\nConectado a MQTT e RabbitMQ.", font=("Arial", 20))
        label.pack(pady=100, padx=100)

    def on_closing(self):
        if self.auth_client: self.auth_client.disconnect()
        if self.mqtt_client: self.mqtt_client.disconnect()
        if self.rabbit_client: self.rabbit_client.close()
        self.destroy()

if __name__ == "__main__":
    app = UserHibridoApp()
    app.mainloop()