import customtkinter as ctk
from mqtt_client import MQTTClient
import datetime
import queue
import uuid

UNIQUE_PREFIX = "ppd-plinio-final/"
COLOR_ONLINE = "#1F6AA5"
COLOR_OFFLINE = "#C21807"
COLOR_VALID = "#009E00"

TOPIC_MGMT_USERS = f"{UNIQUE_PREFIX}sistema/gerenciamento/usuarios"
TOPIC_MGMT_TOPICS = f"{UNIQUE_PREFIX}sistema/gerenciamento/topicos"
TOPIC_MGMT_USERS_WILDCARD = f"{TOPIC_MGMT_USERS}/+"
TOPIC_MGMT_TOPICS_WILDCARD = f"{TOPIC_MGMT_TOPICS}/+"
TOPIC_PRESENCE = f"{UNIQUE_PREFIX}sistema/presenca"
TOPIC_PRESENCE_REQUEST = f"{UNIQUE_PREFIX}sistema/presenca/requisicao"
TOPIC_USER_MSG_BASE = f"{UNIQUE_PREFIX}usuarios"
TOPIC_ACK_BASE = f"{UNIQUE_PREFIX}sistema/ack"
TOPIC_AUTH_REQUEST = f"{UNIQUE_PREFIX}sistema/auth/request"
TOPIC_AUTH_RESPONSE_BASE = f"{UNIQUE_PREFIX}sistema/auth/response"


class UserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aplicação de Usuário MOM")
        self.geometry("400x250")
        self.user_name = None
        self.mqtt_client = None
        self.auth_client = None
        self.users = []
        self.topics = set()
        self.active_subscriptions = set()
        self.user_status = {}
        self.gui_queue = queue.Queue()
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
        self.username_entry.bind("<Return>", lambda event: self.start_login_validation())
        self.status_label = ctk.CTkLabel(self.login_frame, text="")
        self.status_label.pack(pady=(0, 10))

    def start_login_validation(self):
        """ NOVO: Inicia o processo de validação em 2 etapas. """
        self.user_name = self.username_entry.get().strip()
        if not self.user_name:
            self.status_label.configure(text="Nome de usuário não pode ser vazio.", text_color=COLOR_OFFLINE)
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
            self.status_label.configure(text="Erro de conexão. Tente novamente.", text_color=COLOR_OFFLINE)
            self.login_button.configure(state="normal", text="Entrar")

    def handle_auth_response(self, client, userdata, message):
        """ NOVO: Processa a resposta do gerente. """
        payload = message.payload.decode()
        self.auth_client.disconnect()

        if payload == "VALIDO":
            self.status_label.configure(text="Usuário válido! Entrando...", text_color=COLOR_VALID)
            self.after(500, self.proceed_with_main_login)
        else:
            self.status_label.configure(text="Usuário inválido ou não cadastrado.", text_color=COLOR_OFFLINE)
            self.login_button.configure(state="normal", text="Entrar")
            
    def proceed_with_main_login(self):
        """ NOVO: Lógica principal de login, só executa após validação. """
        self.login_frame.destroy()
        self.geometry("900x700")
        self.title(f"MOM - Usuário: {self.user_name}")
        self.setup_main_ui()

        will_payload = f"{self.user_name}:OFFLINE"
        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_message,
                                      will_topic=TOPIC_PRESENCE, will_payload=will_payload, will_retain=True)
        
        if self.mqtt_client.connect():
            self.personal_topic = f"{TOPIC_USER_MSG_BASE}/{self.user_name}"
            self.mqtt_client.subscribe(self.personal_topic)
            self.mqtt_client.subscribe(TOPIC_MGMT_USERS_WILDCARD)
            self.mqtt_client.subscribe(TOPIC_MGMT_TOPICS_WILDCARD)
            self.mqtt_client.subscribe(TOPIC_PRESENCE)
            self.mqtt_client.subscribe(TOPIC_PRESENCE_REQUEST)
            self.request_presence_status()
            self.add_log(f"Conectado como '{self.user_name}'.")
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.process_gui_queue()
        else:
            self.add_log("FALHA AO CONECTAR. Saindo...")
            self.after(2000, self.destroy)

    def process_gui_queue(self):
        try:
            while True:
                task = self.gui_queue.get_nowait()
                if task: task()
        except queue.Empty: pass
        finally:
            self.after(100, self.process_gui_queue)

    def on_message(self, client, userdata, message):
        self.gui_queue.put(lambda: self.handle_message(message.topic, message.payload.decode()))

    def handle_message(self, topic, payload):
        if topic == self.personal_topic:
            if payload:
                self.add_log(f"(Privado) de {payload}")
                self.mqtt_client.publish(f"{TOPIC_ACK_BASE}/{self.user_name}", "ACK")
                self.mqtt_client.publish(self.personal_topic, "", retain=True)
            return

        if topic == TOPIC_PRESENCE:
            self.handle_presence_update(payload)
            return

        if topic == TOPIC_PRESENCE_REQUEST:
            if self.mqtt_client:
                self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:ONLINE", retain=False)
            return
            
        if topic.startswith(TOPIC_MGMT_USERS):
            user = topic.split('/')[-1]
            if not payload:
                if user in self.users: self.users.remove(user)
                if user in self.user_status: del self.user_status[user]
            elif payload == "ADD" and user not in self.users:
                self.users.append(user)
            self.update_users_list_display()
            self.update_send_selectors()
            return
            
        if topic.startswith(TOPIC_MGMT_TOPICS):
            topic_name = topic.split('/')[-1]
            if not payload:
                if topic_name in self.topics: self.topics.discard(topic_name)
                if topic_name in self.active_subscriptions: self.active_subscriptions.discard(topic_name)
            elif payload == "ADD" and topic_name not in self.topics:
                self.topics.add(topic_name)
            self.update_topics_list_display()
            self.update_send_selectors()
            return

        topic_name_only = topic.replace(UNIQUE_PREFIX, "")
        if topic_name_only in self.active_subscriptions:
            if not payload.startswith(f"{self.user_name}:"):
                self.add_log(f"({topic_name_only}) | {payload}")

    def handle_presence_update(self, payload):
        try:
            user_name, status = payload.split(":")
            if self.user_status.get(user_name) != status:
                self.user_status[user_name] = status
                self.update_users_list_display()
        except ValueError: pass

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
        if not topic_name or "Selecione" in topic_name or "Nenhum" in topic_name or not message:
            self.add_log("ALERTA: Selecione um tópico e digite uma mensagem.")
            return
        full_topic_path = f"{UNIQUE_PREFIX}{topic_name}"
        full_message = f"{self.user_name}: {message}"
        self.mqtt_client.publish(full_topic_path, full_message)
        self.add_log(f"Você para ({topic_name}): {message}")
        self.topic_msg_entry.delete(0, "end")

    def send_to_user(self):
        recipient = self.user_combobox.get().strip()
        message = self.user_msg_entry.get().strip()
        if not recipient or "Selecione" in recipient or "Nenhum" in recipient or not message:
            self.add_log("ALERTA: Selecione um usuário e digite uma mensagem.")
            return
        payload = f"{self.user_name}: {message}"
        recipient_topic = f"{TOPIC_USER_MSG_BASE}/{recipient}"
        self.mqtt_client.publish(recipient_topic, payload, retain=True)
        self.add_log(f"Você para (Privado) {recipient}: {message}")
        self.user_msg_entry.delete(0, "end")
        
    def update_send_selectors(self):
        subscribed_topics = sorted(list(self.active_subscriptions))
        if subscribed_topics:
            current_topic = self.topic_combobox.get()
            self.topic_combobox.configure(values=subscribed_topics)
            if current_topic in subscribed_topics:
                self.topic_combobox.set(current_topic)
            else:
                self.topic_combobox.set(subscribed_topics[0])
        else:
            self.topic_combobox.configure(values=["Nenhum tópico inscrito"])
            self.topic_combobox.set("Nenhum tópico inscrito")

        other_users = sorted([u for u in self.users if u != self.user_name])
        if other_users:
            current_user = self.user_combobox.get()
            self.user_combobox.configure(values=other_users)
            if current_user in other_users and "Selecione" not in current_user:
                self.user_combobox.set(current_user)
            else:
                self.user_combobox.set("Selecione um usuário...")
        else:
            self.user_combobox.configure(values=["Nenhum outro usuário"])
            self.user_combobox.set("Nenhum outro usuário")
            
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

    def update_users_list_display(self):
        for widget in self.users_list_frame.winfo_children(): widget.destroy()
        online_users = [u for u in self.users if self.user_status.get(u) == "ONLINE"]
        offline_users = [u for u in self.users if self.user_status.get(u) != "ONLINE"]
        if online_users:
            header = ctk.CTkLabel(self.users_list_frame, text=f"Online ({len(online_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(5, 2))
            for user_name in sorted(online_users):
                self.create_user_list_item(user_name, True)
        if offline_users:
            header = ctk.CTkLabel(self.users_list_frame, text=f"Offline ({len(offline_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(10, 2))
            for user_name in sorted(offline_users):
                self.create_user_list_item(user_name, False)
                
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
        self.destroy()

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

if __name__ == "__main__":
    app = UserApp()
    app.mainloop()