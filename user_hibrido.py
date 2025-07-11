import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import uuid
import datetime
import queue
from rabbitmq_client import RabbitMQClient
from mqtt_client import MQTTClient

UNIQUE_PREFIX = "ppd-hibrido-final/"
COLOR_ONLINE = "#1F6AA5"
COLOR_OFFLINE = "#C21807"
TOPIC_MGMT_USERS = f"{UNIQUE_PREFIX}sistema/gerenciamento/usuarios"
TOPIC_MGMT_TOPICS = f"{UNIQUE_PREFIX}sistema/gerenciamento/topicos"
TOPIC_MGMT_USERS_WILDCARD = f"{TOPIC_MGMT_USERS}/+"
TOPIC_MGMT_TOPICS_WILDCARD = f"{TOPIC_MGMT_TOPICS}/+"
TOPIC_PRESENCE = f"{UNIQUE_PREFIX}sistema/presenca"
TOPIC_PRESENCE_REQUEST = f"{UNIQUE_PREFIX}sistema/presenca/requisicao"
TOPIC_USER_MSG_BASE = f"{UNIQUE_PREFIX}usuarios"
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
        
        self.users = set()
        self.topics = set()
        self.active_subscriptions = set()
        self.user_status = {}
        self.gui_queue = queue.Queue()

        self.create_login_widgets()

    def update_users_list_display(self):
        """Função central e corrigida para desenhar a lista de usuários."""
        for widget in self.users_list_frame.winfo_children():
            widget.destroy()
        
        all_users = sorted(list(self.users))
        
        online_users = [u for u in all_users if self.user_status.get(u) == "ONLINE"]
        offline_users = [u for u in all_users if self.user_status.get(u) != "ONLINE"]

        if online_users:
            header = ctk.CTkLabel(self.users_list_frame, text=f"Online ({len(online_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(5, 2))
            for user_name in online_users:
                self.create_user_list_item(user_name, True)
        
        if offline_users:
            header = ctk.CTkLabel(self.users_list_frame, text=f"Offline ({len(offline_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(10, 2))
            for user_name in offline_users:
                self.create_user_list_item(user_name, False)

    def create_login_widgets(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        label = ctk.CTkLabel(self.login_frame, text="Digite seu nome de usuário:", font=ctk.CTkFont(size=15))
        label.pack(pady=20, padx=20)
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
        for widget in self.winfo_children(): widget.destroy()
        self.geometry("900x700")
        self.title(f"MOM Híbrido - Usuário: {self.user_name}")
        try:
            self.setup_main_ui()
            self.rabbit_client = RabbitMQClient()
            self.add_log("Conexão com RabbitMQ estabelecida.")
            will_payload = f"{self.user_name}:OFFLINE"
            self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_mqtt_message,
                                          will_topic=TOPIC_PRESENCE, will_payload=will_payload, will_retain=True)
            self.mqtt_client.connect()
            self.add_log("Conexão com MQTT estabelecida.")
            self.start_consumers()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.process_gui_queue()
        except Exception as e:
            messagebox.showerror("Erro de Conexão Híbrida", f"Falha ao conectar a um dos serviços: {e}")
            self.destroy()

    def start_consumers(self):
        rabbit_queue = f"queue_{self.user_name}"
        self.rabbit_client.start_consuming_from_queue(rabbit_queue, self.on_rabbit_message)
        self.add_log(f"Ouvindo fila de mensagens offline: {rabbit_queue}")
        self.mqtt_client.subscribe(TOPIC_MGMT_USERS_WILDCARD)
        self.mqtt_client.subscribe(TOPIC_MGMT_TOPICS_WILDCARD)
        self.mqtt_client.subscribe(TOPIC_PRESENCE)
        self.mqtt_client.subscribe(TOPIC_PRESENCE_REQUEST)
        self.request_presence_status()
        
    def process_gui_queue(self):
        try:
            while True:
                task, args = self.gui_queue.get_nowait()
                task(*args)
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_gui_queue)

    def on_mqtt_message(self, client, userdata, message):
        self.gui_queue.put((self.handle_mqtt_message, (message.topic, message.payload.decode())))

    def on_rabbit_message(self, ch, method, properties, body):
        self.gui_queue.put((self.handle_rabbit_message, (body.decode(),)))

    def handle_rabbit_message(self, payload):
        self.add_log(f"[Mensagem Direta] {payload}")
        
    def handle_mqtt_message(self, topic, payload):
        if topic == TOPIC_PRESENCE: self.handle_presence_update(payload)
        elif topic == TOPIC_PRESENCE_REQUEST: self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:ONLINE", retain=False)
        elif topic.startswith(TOPIC_MGMT_USERS): self.handle_user_sync(topic, payload)
        elif topic.startswith(TOPIC_MGMT_TOPICS): self.handle_topic_sync(topic, payload)
        else:
            topic_name_only = topic.replace(UNIQUE_PREFIX, "")
            if topic_name_only in self.active_subscriptions and not payload.startswith(f"{self.user_name}:"):
                self.add_log(f"({topic_name_only}) | {payload}")

    def handle_presence_update(self, payload):
        try:
            user_name, status = payload.split(":")
            if self.user_status.get(user_name) != status:
                self.user_status[user_name] = status
                self.update_users_list_display()
        except ValueError: pass

    def handle_user_sync(self, topic, payload):
        user = topic.split('/')[-1]
        if not payload:
            self.users.discard(user)
            if user in self.user_status: del self.user_status[user]
        elif payload == "ADD":
            self.users.add(user)
        self.update_users_list_display()
        self.update_send_selectors()

    def handle_topic_sync(self, topic, payload):
        topic_name = topic.split('/')[-1]
        if not payload:
            self.topics.discard(topic_name)
            self.active_subscriptions.discard(topic_name)
        elif payload == "ADD":
            self.topics.add(topic_name)
        self.update_topics_list_display()
        self.update_send_selectors()

    def request_presence_status(self):
        self.mqtt_client.publish(TOPIC_PRESENCE_REQUEST, "who_is_online")
        self.add_log("Sincronizando status de presença...")

    def setup_main_ui(self):
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1); left_frame.grid_rowconfigure(3, weight=1)
        topics_label = ctk.CTkLabel(left_frame, text="Tópicos do Sistema", font=ctk.CTkFont(size=14, weight="bold"))
        topics_label.grid(row=0, column=0, padx=10, pady=10)
        self.topics_list_frame = ctk.CTkScrollableFrame(left_frame)
        self.topics_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        users_label = ctk.CTkLabel(left_frame, text="Usuários do Sistema", font=ctk.CTkFont(size=14, weight="bold"))
        users_label.grid(row=2, column=0, padx=10, pady=10)
        self.users_list_frame = ctk.CTkScrollableFrame(left_frame)
        self.users_list_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1); right_frame.grid_rowconfigure(0, weight=1)
        self.log_textbox = ctk.CTkTextbox(right_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.topic_combobox = ctk.CTkComboBox(right_frame, values=[], button_hover_color=COLOR_ONLINE)
        self.topic_combobox.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.topic_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o tópico")
        self.topic_msg_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        send_topic_button = ctk.CTkButton(right_frame, text="Enviar para Tópico", command=self.send_to_topic)
        send_topic_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.user_combobox = ctk.CTkComboBox(right_frame, values=[], button_hover_color=COLOR_ONLINE)
        self.user_combobox.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.user_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o usuário")
        self.user_msg_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        send_user_button = ctk.CTkButton(right_frame, text="Enviar para Usuário", command=self.send_to_user)
        send_user_button.grid(row=3, column=1, sticky="ew", padx=10, pady=10)
        
    def send_to_topic(self):
        topic_name = self.topic_combobox.get().strip()
        message = self.topic_msg_entry.get().strip()
        if not topic_name or "Selecione" in topic_name or "Nenhum" in topic_name or not message: return
        full_topic_path = f"{UNIQUE_PREFIX}{topic_name}"
        full_message = f"{self.user_name}: {message}"
        self.mqtt_client.publish(full_topic_path, full_message)
        self.add_log(f"Você para ({topic_name}): {message}")
        self.topic_msg_entry.delete(0, ctk.END)

    def send_to_user(self):
        recipient = self.user_combobox.get().strip()
        message = self.user_msg_entry.get().strip()
        if not recipient or "Selecione" in recipient or "Nenhum" in recipient or not message: return
        queue_name = f"queue_{recipient}"
        payload = f"de {self.user_name}: {message}"
        self.rabbit_client.publish_to_queue(queue_name, payload)
        self.add_log(f"Você para {recipient} (Privado): {message}")
        self.user_msg_entry.delete(0, ctk.END)
        
    def update_send_selectors(self):
        subscribed_topics = sorted(list(self.active_subscriptions))
        self.topic_combobox.configure(values=subscribed_topics)
        if subscribed_topics: self.topic_combobox.set(subscribed_topics[0])
        else: self.topic_combobox.set("Nenhum tópico inscrito")
        other_users = sorted([u for u in list(self.users) if u != self.user_name])
        self.user_combobox.configure(values=other_users)
        if other_users: self.user_combobox.set("Selecione um usuário...")
        else: self.user_combobox.set("Nenhum outro usuário")
            
    def subscribe_to_topic(self, topic_name):
        full_topic_path = f"{UNIQUE_PREFIX}{topic_name}"
        self.mqtt_client.subscribe(full_topic_path)
        self.active_subscriptions.add(topic_name)
        self.add_log(f"Inscrito no tópico: {topic_name}")
        self.update_topics_list_display()
        self.update_send_selectors()

    def unsubscribe_from_topic(self, topic_name):
        full_topic_path = f"{UNIQUE_PREFIX}{topic_name}"
        self.mqtt_client.unsubscribe(full_topic_path)
        self.active_subscriptions.discard(topic_name)
        self.add_log(f"Inscrição cancelada para: {topic_name}")
        self.update_topics_list_display()
        self.update_send_selectors()
        
    def update_topics_list_display(self):
        for widget in self.topics_list_frame.winfo_children(): widget.destroy()
        for topic_name in sorted(list(self.topics)):
            is_subscribed = topic_name in self.active_subscriptions
            btn_text = f"{topic_name} (Sair)" if is_subscribed else topic_name
            btn_fg_color = ("#4A4A4A", "#555555") if is_subscribed else ("#3B8ED0", "#1F6AA5")
            btn_command = lambda t=topic_name, sub=is_subscribed: self.unsubscribe_from_topic(t) if sub else self.subscribe_to_topic(t)
            btn = ctk.CTkButton(self.topics_list_frame, text=btn_text, command=btn_command, fg_color=btn_fg_color)
            btn.pack(padx=10, pady=5, fill="x")

    def create_user_list_item(self, user_name, is_online):
        color = COLOR_ONLINE if is_online else COLOR_OFFLINE
        item_frame = ctk.CTkFrame(self.users_list_frame, fg_color="transparent")
        item_frame.pack(fill="x", padx=5)
        dot_label = ctk.CTkLabel(item_frame, text="●", text_color=color, font=ctk.CTkFont(size=18))
        dot_label.pack(side="left", padx=(5,2))
        name_label = ctk.CTkLabel(item_frame, text=user_name, anchor="w")
        name_label.pack(side="left")

    def on_closing(self):
        if self.auth_client: self.auth_client.disconnect()
        if self.mqtt_client and self.user_name:
            self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:OFFLINE", retain=True)
            self.mqtt_client.disconnect()
        if self.rabbit_client: self.rabbit_client.close()
        self.destroy()

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

if __name__ == "__main__":
    app = UserHibridoApp()
    app.mainloop()