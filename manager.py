import customtkinter as ctk
from mqtt_client import MQTTClient

# --- Constantes para os Tópicos de Gerenciamento ---
TOPIC_USERS = "sistema/gerenciamento/usuarios"
TOPIC_TOPICS = "sistema/gerenciamento/topicos"

class ManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuração da Janela Principal ---
        self.title("Gerenciador MOM")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing) # Lida com o fechamento da janela

        # --- Layout da Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Inicialização dos Atributos ---
        self.users = []
        self.topics = []
        self.user_widgets = []
        self.topic_widgets = []

        # --- Criação dos Widgets ---
        self.create_widgets()

        # --- Configuração e Conexão MQTT ---
        self.mqtt_client = MQTTClient(on_message_callback=self.on_message)
        self.mqtt_client.connect()
        # Inscreve-se nos tópicos para receber atualizações (importante se houver múltiplos gerentes)
        self.mqtt_client.subscribe(f"{TOPIC_USERS}/+")
        self.mqtt_client.subscribe(f"{TOPIC_TOPICS}/+")
        self.add_log("Cliente MQTT Conectado e inscrito nos tópicos de gerenciamento.")

    def on_message(self, client, userdata, message):
        """Callback para processar mensagens MQTT recebidas."""
        topic = message.topic
        payload = message.payload.decode()
        self.add_log(f"Mensagem recebida | Tópico: {topic} | Payload: {payload}")
        # Lógica para processar adições/remoções de outros gerentes será adicionada aqui
        
    def create_widgets(self):
        # --- Frame de Gerenciamento de Usuários ---
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


        # --- Frame de Gerenciamento de Tópicos ---
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

        # --- Frame de Contagem de Mensagens ---
        counts_frame = ctk.CTkFrame(self)
        counts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        counts_frame.grid_columnconfigure(0, weight=1)

        counts_label = ctk.CTkLabel(counts_frame, text="Mensagens Pendentes por Usuário", font=ctk.CTkFont(size=15, weight="bold"))
        counts_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.counts_display_frame = ctk.CTkScrollableFrame(counts_frame)
        self.counts_display_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        counts_frame.grid_rowconfigure(1, weight=1)

        # --- Frame de Log de Eventos ---
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
        
        self.users.append(user_name)
        self.update_user_list_display()
        # Publica para notificar outros sobre o novo usuário
        self.mqtt_client.publish(f"{TOPIC_USERS}/{user_name}", "ADD")
        self.add_log(f"Usuário '{user_name}' adicionado e notificação publicada.")
        self.user_entry.delete(0, "end")

    def add_topic(self):
        topic_name = self.topic_entry.get().strip()
        if not topic_name:
            self.add_log("ERRO: Nome do tópico não pode ser vazio.")
            return
        if topic_name in self.topics:
            self.add_log(f"ERRO: Tópico '{topic_name}' já existe.")
            return
            
        self.topics.append(topic_name)
        self.update_topic_list_display()
        # Publica para notificar outros sobre o novo tópico
        self.mqtt_client.publish(f"{TOPIC_TOPICS}/{topic_name}", "ADD")
        self.add_log(f"Tópico '{topic_name}' adicionado e notificação publicada.")
        self.topic_entry.delete(0, "end")

    def update_user_list_display(self):
        # Limpa a lista antiga
        for widget in self.user_widgets:
            widget.destroy()
        self.user_widgets.clear()
        
        # Adiciona os usuários da lista atual
        for user_name in self.users:
            label = ctk.CTkLabel(self.user_list_frame, text=user_name)
            label.pack(anchor="w", padx=10)
            self.user_widgets.append(label)

    def update_topic_list_display(self):
        # Limpa a lista antiga
        for widget in self.topic_widgets:
            widget.destroy()
        self.topic_widgets.clear()
        
        # Adiciona os tópicos da lista atual
        for topic_name in self.topics:
            label = ctk.CTkLabel(self.topic_list_frame, text=topic_name)
            label.pack(anchor="w", padx=10)
            self.topic_widgets.append(label)

    def on_closing(self):
        """Função chamada ao fechar a janela."""
        self.mqtt_client.disconnect()
        self.destroy()

if __name__ == "__main__":
    app = ManagerApp()
    app.mainloop()