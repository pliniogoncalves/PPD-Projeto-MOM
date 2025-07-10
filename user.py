# user.py (Corrigido com Fila)
import customtkinter as ctk
from mqtt_client import MQTTClient
import datetime
import queue

# ... (Constantes continuam as mesmas) ...
TOPIC_USERS_WILDCARD = "sistema/gerenciamento/usuarios/+"
TOPIC_TOPICS_WILDCARD = "sistema/gerenciamento/topicos/+"

class UserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aplicação de Usuário MOM")
        self.geometry("400x250")
        self.user_name = None
        self.mqtt_client = None
        self.users = []
        self.topics = []
        self.gui_queue = queue.Queue() # Fila
        self.create_login_widgets()

    def process_gui_queue(self):
        try:
            while True:
                task = self.gui_queue.get_nowait()
                if task: task()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_gui_queue)

    def login(self):
        self.user_name = self.username_entry.get().strip()
        if not self.user_name: return
        self.login_frame.destroy()
        self.geometry("900x700")
        self.title(f"MOM - Usuário: {self.user_name}")
        self.setup_main_ui()
        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_message)
        self.mqtt_client.connect()
        self.personal_topic = f"usuarios/{self.user_name}"
        self.mqtt_client.subscribe(self.personal_topic)
        self.mqtt_client.subscribe(TOPIC_USERS_WILDCARD)
        self.mqtt_client.subscribe(TOPIC_TOPICS_WILDCARD)
        self.add_log(f"Conectado como '{self.user_name}'. Escutando em '{self.personal_topic}'.")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.process_gui_queue() # Inicia o processador

    def on_message(self, client, userdata, message):
        # Coloca a tarefa de processar na fila
        self.gui_queue.put(lambda: self.handle_message(message.topic, message.payload.decode()))

    def handle_message(self, topic, payload):
        # Lógica que antes estava em on_message
        if topic == self.personal_topic:
            self.add_log(f"(Privado) de {payload}")
            ack_topic = f"sistema/ack/{self.user_name}"
            self.mqtt_client.publish(ack_topic, "ACK")
        elif topic in self.topics:
            self.add_log(f"({topic}) | {payload}")
        elif topic.startswith("sistema/gerenciamento/usuarios/"):
            user = topic.split('/')[-1]
            if not payload and user in self.users: self.users.remove(user) # Remove
            elif payload == "ADD" and user not in self.users: self.users.append(user) # Adiciona
            self.update_users_list_display()
        elif topic.startswith("sistema/gerenciamento/topicos/"):
            new_topic = topic.split('/')[-1]
            if not payload and new_topic in self.topics: self.topics.remove(new_topic) # Remove
            elif payload == "ADD" and new_topic not in self.topics: self.topics.append(new_topic) # Adiciona
            self.update_topics_list_display()
    
    # O resto do código continua o mesmo...
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

    def setup_main_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_rowconfigure(3, weight=1)
        topics_label = ctk.CTkLabel(left_frame, text="Tópicos do Sistema", font=ctk.CTkFont(size=14, weight="bold"))
        topics_label.grid(row=0, column=0, padx=10, pady=10)
        self.topics_list_frame = ctk.CTkFrame(left_frame)
        self.topics_list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        users_label = ctk.CTkLabel(left_frame, text="Usuários Online", font=ctk.CTkFont(size=14, weight="bold"))
        users_label.grid(row=2, column=0, padx=10, pady=10)
        self.users_list_frame = ctk.CTkFrame(left_frame)
        self.users_list_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(0, weight=1)
        self.log_textbox = ctk.CTkTextbox(right_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.topic_entry = ctk.CTkEntry(right_frame, placeholder_text="Tópico para enviar msg")
        self.topic_entry.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.topic_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o tópico")
        self.topic_msg_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        send_topic_button = ctk.CTkButton(right_frame, text="Enviar para Tópico", command=self.send_to_topic)
        send_topic_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        self.user_entry = ctk.CTkEntry(right_frame, placeholder_text="Usuário para enviar msg")
        self.user_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.user_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o usuário")
        self.user_msg_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        send_user_button = ctk.CTkButton(right_frame, text="Enviar para Usuário (Offline)", command=self.send_to_user)
        send_user_button.grid(row=3, column=1, sticky="ew", padx=10, pady=10)

    def send_to_topic(self):
        topic = self.topic_entry.get().strip()
        message = self.topic_msg_entry.get().strip()
        if not topic or not message:
            self.add_log("ALERTA: Tópico e mensagem não podem ser vazios.")
            return
        full_message = f"{self.user_name}: {message}"
        self.mqtt_client.publish(topic, full_message)
        self.add_log(f"Você para ({topic}): {message}")
        self.topic_entry.delete(0, "end")
        self.topic_msg_entry.delete(0, "end")

    def send_to_user(self):
        recipient = self.user_entry.get().strip()
        message = self.user_msg_entry.get().strip()
        if not recipient or not message:
            self.add_log("ALERTA: Usuário e mensagem não podem ser vazios.")
            return
        payload = f"{self.user_name}: {message}"
        recipient_topic = f"usuarios/{recipient}"
        self.mqtt_client.publish(recipient_topic, payload, retain=True)
        self.add_log(f"Você para (Privado) {recipient}: {message}")
        self.user_entry.delete(0, "end")
        self.user_msg_entry.delete(0, "end")

    def subscribe_to_topic(self, topic):
        self.mqtt_client.subscribe(topic)
        self.add_log(f"Inscrito no tópico: {topic}")

    def update_topics_list_display(self):
        for widget in self.topics_list_frame.winfo_children(): widget.destroy()
        for topic in sorted(self.topics):
            btn = ctk.CTkButton(self.topics_list_frame, text=topic, command=lambda t=topic: self.subscribe_to_topic(t))
            btn.pack(padx=10, pady=5, fill="x")

    def update_users_list_display(self):
        for widget in self.users_list_frame.winfo_children(): widget.destroy()
        for user in sorted(self.users):
            label = ctk.CTkLabel(self.users_list_frame, text=user)
            label.pack(padx=10, pady=5, anchor="w")

    def add_log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
        
    def on_closing(self):
        if self.mqtt_client: self.mqtt_client.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = UserApp()
    app.mainloop()