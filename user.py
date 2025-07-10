import customtkinter as ctk
from mqtt_client import MQTTClient
import datetime
import queue

COLOR_ONLINE = "#1F6AA5"
COLOR_OFFLINE = "#C21807"

TOPIC_USERS_WILDCARD = "sistema/gerenciamento/usuarios/+"
TOPIC_TOPICS_WILDCARD = "sistema/gerenciamento/topicos/+"
TOPIC_PRESENCE = "sistema/presenca"
TOPIC_PRESENCE_REQUEST = "sistema/presenca/requisicao"


class UserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aplicação de Usuário MOM")
        self.geometry("400x250")
        self.user_name = None
        self.mqtt_client = None
        self.users = []
        self.topics = []
        self.active_subscriptions = set()
        self.user_status = {}
        self.gui_queue = queue.Queue()
        self.create_login_widgets()

    def process_gui_queue(self):
        try:
            while True:
                task = self.gui_queue.get_nowait()
                if task: task()
        except queue.Empty: pass
        finally:
            self.after(100, self.process_gui_queue)

    def login(self):
        self.user_name = self.username_entry.get().strip()
        if not self.user_name: return
        self.login_frame.destroy()
        self.geometry("900x700")
        self.title(f"MOM - Usuário: {self.user_name}")
        self.setup_main_ui()

        will_payload = f"{self.user_name}:OFFLINE"
        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_message,
                                      will_topic=TOPIC_PRESENCE, will_payload=will_payload, will_retain=True)
        
        if self.mqtt_client.connect():
            self.personal_topic = f"usuarios/{self.user_name}"
            self.mqtt_client.subscribe(self.personal_topic)
            self.mqtt_client.subscribe(TOPIC_USERS_WILDCARD)
            self.mqtt_client.subscribe(TOPIC_TOPICS_WILDCARD)
            self.mqtt_client.subscribe(TOPIC_PRESENCE)
            self.mqtt_client.subscribe(TOPIC_PRESENCE_REQUEST)
            
            self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:ONLINE", retain=False)
            self.request_presence_status()
            
            self.add_log(f"Conectado como '{self.user_name}'. Escutando em '{self.personal_topic}'.")
            self.protocol("WM_DELETE_WINDOW", self.on_closing)
            self.process_gui_queue()
        else:
            self.add_log("FALHA AO CONECTAR. Saindo...")
            self.after(2000, self.destroy)

    def on_message(self, client, userdata, message):
        self.gui_queue.put(lambda: self.handle_message(message.topic, message.payload.decode()))

    def handle_message(self, topic, payload):
        if topic == self.personal_topic:
            self.add_log(f"(Privado) de {payload}")
            self.mqtt_client.publish(f"sistema/ack/{self.user_name}", "ACK")
        elif topic == TOPIC_PRESENCE:
            self.handle_presence_update(payload)
        elif topic == TOPIC_PRESENCE_REQUEST:
            self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:ONLINE", retain=False)
        elif topic.startswith("sistema/gerenciamento/usuarios/"):
            user = topic.split('/')[-1]
            if not payload:
                if user in self.users: self.users.remove(user)
                if user in self.user_status: del self.user_status[user]
            elif payload == "ADD" and user not in self.users:
                self.users.append(user)
            self.update_users_list_display()
            self.update_send_selectors()
        elif topic.startswith("sistema/gerenciamento/topicos/"):
            new_topic = topic.split('/')[-1]
            if not payload and new_topic in self.topics:
                self.topics.remove(new_topic)
                if new_topic in self.active_subscriptions: self.active_subscriptions.discard(new_topic)
            elif payload == "ADD" and new_topic not in self.topics:
                self.topics.append(new_topic)
            self.update_topics_list_display()
            self.update_send_selectors()
        elif topic in self.active_subscriptions:
            self.add_log(f"({topic}) | {payload}")

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
        send_user_button = ctk.CTkButton(right_frame, text="Enviar para Usuário (Offline)", command=self.send_to_user)
        send_user_button.grid(row=3, column=1, sticky="ew", padx=10, pady=10)
        
    def send_to_topic(self):
        topic = self.topic_combobox.get().strip()
        message = self.topic_msg_entry.get().strip()
        if not topic or not message:
            self.add_log("ALERTA: Selecione um tópico e digite uma mensagem.")
            return
        full_message = f"{self.user_name}: {message}"
        self.mqtt_client.publish(topic, full_message)
        self.add_log(f"Você para ({topic}): {message}")
        self.topic_msg_entry.delete(0, "end")

    def send_to_user(self):
        recipient = self.user_combobox.get().strip()
        message = self.user_msg_entry.get().strip()
        if not recipient or not message:
            self.add_log("ALERTA: Selecione um usuário e digite uma mensagem.")
            return
        payload = f"{self.user_name}: {message}"
        recipient_topic = f"usuarios/{recipient}"
        self.mqtt_client.publish(recipient_topic, payload, retain=True)
        self.add_log(f"Você para (Privado) {recipient}: {message}")
        self.user_msg_entry.delete(0, "end")
        
    def update_send_selectors(self):
        subscribed_topics = sorted(list(self.active_subscriptions))
        self.topic_combobox.configure(values=subscribed_topics)
        if subscribed_topics: self.topic_combobox.set(subscribed_topics[0])
        else: self.topic_combobox.set("")

        all_users = sorted(self.users)
        self.user_combobox.configure(values=all_users)
        if all_users: self.user_combobox.set(all_users[0])
        else: self.user_combobox.set("")
            
    def subscribe_to_topic(self, topic):
        self.mqtt_client.subscribe(topic)
        self.active_subscriptions.add(topic)
        self.add_log(f"Inscrito no tópico: {topic}")
        self.update_topics_list_display()
        self.update_send_selectors()

    def unsubscribe_from_topic(self, topic):
        self.mqtt_client.unsubscribe(topic)
        self.active_subscriptions.discard(topic)
        self.add_log(f"Inscrição cancelada para: {topic}")
        self.update_topics_list_display()
        self.update_send_selectors()

    def update_topics_list_display(self):
        for widget in self.topics_list_frame.winfo_children(): widget.destroy()
        
        for topic in sorted(self.topics):
            is_subscribed = topic in self.active_subscriptions
            
            btn_text = f"{topic} (Sair)" if is_subscribed else topic
            btn_fg_color = ("#4A4A4A", "#555555") if is_subscribed else ("#3B8ED0", "#1F6AA5")
            btn_command = lambda t=topic: self.unsubscribe_from_topic(t) if is_subscribed else self.subscribe_to_topic(t)

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
        if self.mqtt_client and self.user_name:
            self.mqtt_client.publish(TOPIC_PRESENCE, f"{self.user_name}:OFFLINE", retain=True)
            self.mqtt_client.disconnect()
        self.destroy()

    def create_login_widgets(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(self.login_frame, text="Digite seu nome de usuário:", font=ctk.CTkFont(size=15))
        label.pack(pady=10)
        self.username_entry = ctk.CTkEntry(self.login_frame, width=200)
        self.username_entry.pack(pady=10)
        login_button = ctk.CTkButton(self.login_frame, text="Entrar", command=self.login)
        login_button.pack(pady=20)
        self.username_entry.bind("<Return>", lambda event: self.login())

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

if __name__ == "__main__":
    app = UserApp()
    app.mainloop()