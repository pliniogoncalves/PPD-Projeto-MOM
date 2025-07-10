# manager.py (Corrigido com Fila)
import customtkinter as ctk
from mqtt_client import MQTTClient
import queue

# ... (Constantes continuam as mesmas) ...
TOPIC_USERS = "sistema/gerenciamento/usuarios"
TOPIC_TOPICS = "sistema/gerenciamento/topicos"
TOPIC_USER_MSG_WILDCARD = "usuarios/+"
TOPIC_ACK_WILDCARD = "sistema/ack/+"


class ManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gerenciador MOM")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.users = []
        self.topics = []
        self.message_counts = {}
        self.create_widgets()

        # NOVO: Fila para comunicação thread-safe com a GUI
        self.gui_queue = queue.Queue()

        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_message)
        self.mqtt_client.connect()
        self.mqtt_client.subscribe(f"{TOPIC_USERS}/+")
        self.mqtt_client.subscribe(f"{TOPIC_TOPICS}/+")
        self.mqtt_client.subscribe(TOPIC_USER_MSG_WILDCARD)
        self.mqtt_client.subscribe(TOPIC_ACK_WILDCARD)
        self.add_log("Cliente MQTT conectado e inscrito nos tópicos.")

        # NOVO: Inicia o processador da fila da GUI
        self.process_gui_queue()

    def process_gui_queue(self):
        """ Processa tarefas da fila para atualizar a GUI de forma segura. """
        try:
            while True:
                task = self.gui_queue.get_nowait()
                if task:
                    task()
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_gui_queue)

    def on_message(self, client, userdata, message):
        topic = message.topic
        payload = message.payload.decode()
        
        # MODIFICADO: Coloca as chamadas de atualização na fila em vez de executar diretamente
        if topic.startswith("usuarios/"):
            self.gui_queue.put(lambda: self.handle_user_message(topic))
        elif topic.startswith("sistema/ack/"):
            self.gui_queue.put(lambda: self.handle_ack_message(topic))
        elif topic.startswith(TOPIC_USERS):
            self.gui_queue.put(lambda: self.handle_user_sync(topic, payload))
        elif topic.startswith(TOPIC_TOPICS):
            self.gui_queue.put(lambda: self.handle_topic_sync(topic, payload))

    # NOVOS MÉTODOS: Lógica movida do on_message para ser chamada pela fila
    def handle_user_message(self, topic):
        user_name = topic.split('/')[1]
        if user_name in self.message_counts:
            self.message_counts[user_name] += 1
            self.add_log(f"INFO: Mensagem enviada para {user_name}. Contador incrementado.")
            self.update_counts_display()

    def handle_ack_message(self, topic):
        user_name = topic.split('/')[2]
        if user_name in self.message_counts and self.message_counts[user_name] > 0:
            self.message_counts[user_name] -= 1
            self.add_log(f"INFO: {user_name} confirmou recebimento. Contador decrementado.")
            self.update_counts_display()

    def handle_user_sync(self, topic, payload):
        user_name = topic.split('/')[-1]
        if payload == "ADD":
            if user_name not in self.users:
                self.users.append(user_name)
                if user_name not in self.message_counts: self.message_counts[user_name] = 0
                self.add_log(f"INFO: Usuário '{user_name}' sincronizado.")
                self.update_all_displays()
        elif not payload:
            if user_name in self.users:
                self.users.remove(user_name)
                if user_name in self.message_counts: del self.message_counts[user_name]
                self.add_log(f"INFO: Usuário '{user_name}' removido.")
                self.update_all_displays()

    def handle_topic_sync(self, topic, payload):
        topic_name = topic.split('/')[-1]
        if payload == "ADD":
            if topic_name not in self.topics:
                self.topics.append(topic_name)
                self.add_log(f"INFO: Tópico '{topic_name}' sincronizado.")
                self.update_topic_list_display()
        elif not payload:
            if topic_name in self.topics:
                self.topics.remove(topic_name)
                self.add_log(f"INFO: Tópico '{topic_name}' removido.")
                self.update_topic_list_display()
    
    # O resto do código (create_widgets, add_log, add_user, etc.) continua o mesmo...
    def create_widgets(self):
        self.user_widgets = []
        self.topic_widgets = []
        self.counts_widgets = []
        user_frame = ctk.CTkFrame(self)
        user_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        user_frame.grid_columnconfigure(0, weight=1)
        user_label = ctk.CTkLabel(user_frame, text="Gerenciar Usuários", font=ctk.CTkFont(size=15, weight="bold"))
        user_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.user_entry = ctk.CTkEntry(user_frame, placeholder_text="Nome do usuário")
        self.user_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        add_user_button = ctk.CTkButton(user_frame, text="Adicionar Usuário", command=self.add_user)
        add_user_button.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.user_list_frame = ctk.CTkScrollableFrame(user_frame, label_text="Usuários Registrados:")
        self.user_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        user_frame.grid_rowconfigure(3, weight=1)
        topic_frame = ctk.CTkFrame(self)
        topic_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        topic_frame.grid_columnconfigure(0, weight=1)
        topic_label = ctk.CTkLabel(topic_frame, text="Gerenciar Tópicos", font=ctk.CTkFont(size=15, weight="bold"))
        topic_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.topic_entry = ctk.CTkEntry(topic_frame, placeholder_text="Nome do tópico")
        self.topic_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        add_topic_button = ctk.CTkButton(topic_frame, text="Adicionar Tópico", command=self.add_topic)
        add_topic_button.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.topic_list_frame = ctk.CTkScrollableFrame(topic_frame, label_text="Tópicos Oficiais:")
        self.topic_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        topic_frame.grid_rowconfigure(3, weight=1)
        counts_frame = ctk.CTkFrame(self)
        counts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        counts_frame.grid_columnconfigure(0, weight=1)
        counts_frame.grid_rowconfigure(1, weight=1)
        counts_label = ctk.CTkLabel(counts_frame, text="Mensagens Pendentes por Usuário", font=ctk.CTkFont(size=15, weight="bold"))
        counts_label.grid(row=0, column=0, padx=10, pady=10)
        self.counts_display_frame = ctk.CTkScrollableFrame(counts_frame)
        self.counts_display_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        log_label = ctk.CTkLabel(log_frame, text="Log de Eventos", font=ctk.CTkFont(size=15, weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def add_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def add_user(self):
        user_name = self.user_entry.get().strip()
        if not user_name:
            self.add_log("ERRO: Nome do usuário não pode ser vazio.")
            return
        if user_name in self.users:
            self.add_log(f"ERRO: Usuário '{user_name}' já existe.")
            return
        self.mqtt_client.publish(f"{TOPIC_USERS}/{user_name}", "ADD", retain=True)
        self.add_log(f"Comando para adicionar usuário '{user_name}' publicado.")
        self.user_entry.delete(0, "end")

    def remove_user(self, user_name):
        self.mqtt_client.publish(f"{TOPIC_USERS}/{user_name}", "", retain=True)
        self.add_log(f"Comando para remover usuário '{user_name}' publicado.")

    def add_topic(self):
        topic_name = self.topic_entry.get().strip()
        if not topic_name:
            self.add_log("ERRO: Nome do tópico não pode ser vazio.")
            return
        if topic_name in self.topics:
            self.add_log(f"ERRO: Tópico '{topic_name}' já existe.")
            return
        self.mqtt_client.publish(f"{TOPIC_TOPICS}/{topic_name}", "ADD", retain=True)
        self.add_log(f"Comando para adicionar tópico '{topic_name}' publicado.")
        self.topic_entry.delete(0, "end")

    def remove_topic(self, topic_name):
        self.mqtt_client.publish(f"{TOPIC_TOPICS}/{topic_name}", "", retain=True)
        self.add_log(f"Comando para remover tópico '{topic_name}' publicado.")

    def update_all_displays(self):
        self.update_user_list_display()
        self.update_counts_display()

    def update_user_list_display(self):
        for widget in self.user_list_frame.winfo_children():
            widget.destroy()
        
        for user_name in sorted(self.users):
            item_frame = ctk.CTkFrame(self.user_list_frame)
            item_frame.pack(fill="x", padx=5, pady=2)
            item_frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(item_frame, text=user_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=5)
            remove_button = ctk.CTkButton(item_frame, text="Remover", width=70, command=lambda name=user_name: self.remove_user(name))
            remove_button.grid(row=0, column=1, padx=5)

    def update_topic_list_display(self):
        for widget in self.topic_list_frame.winfo_children():
            widget.destroy()
        
        for topic_name in sorted(self.topics):
            item_frame = ctk.CTkFrame(self.topic_list_frame)
            item_frame.pack(fill="x", padx=5, pady=2)
            item_frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(item_frame, text=topic_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=5)
            remove_button = ctk.CTkButton(item_frame, text="Remover", width=70, command=lambda name=topic_name: self.remove_topic(name))
            remove_button.grid(row=0, column=1, padx=5)

    def update_counts_display(self):
        for widget in self.counts_display_frame.winfo_children():
            widget.destroy()
        
        for user_name, count in sorted(self.message_counts.items()):
            label_text = f"{user_name}: {count}"
            label = ctk.CTkLabel(self.counts_display_frame, text=label_text, anchor="w")
            label.pack(fill="x", padx=10, pady=2)

    def on_closing(self):
        self.mqtt_client.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = ManagerApp()
    app.mainloop()