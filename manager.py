import customtkinter as ctk
from mqtt_client import MQTTClient

class ManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Configuração da Janela Principal ---
        self.title("Gerenciador MOM")
        self.geometry("800x600")

        # --- Layout da Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Inicialização dos Atributos ---
        self.users = []
        self.topics = []

        # --- Criação dos Widgets ---
        self.create_widgets()
        
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
        
        self.user_list_frame = ctk.CTkFrame(user_frame)
        self.user_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        user_frame.grid_rowconfigure(3, weight=1)
        user_list_label = ctk.CTkLabel(self.user_list_frame, text="Usuários Registrados:")
        user_list_label.pack(padx=10, pady=5, anchor="w")


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
        
        self.topic_list_frame = ctk.CTkFrame(topic_frame)
        self.topic_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        topic_frame.grid_rowconfigure(3, weight=1)
        topic_list_label = ctk.CTkLabel(self.topic_list_frame, text="Tópicos Oficiais:")
        topic_list_label.pack(padx=10, pady=5, anchor="w")

        # --- Frame de Contagem de Mensagens ---
        counts_frame = ctk.CTkFrame(self)
        counts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        counts_frame.grid_columnconfigure(0, weight=1)

        counts_label = ctk.CTkLabel(counts_frame, text="Mensagens Pendentes por Usuário", font=ctk.CTkFont(size=15, weight="bold"))
        counts_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.counts_display_frame = ctk.CTkFrame(counts_frame)
        self.counts_display_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        counts_frame.grid_rowconfigure(1, weight=1)

        # --- Frame de Log de Eventos ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        log_label = ctk.CTkLabel(log_frame, text="Log de Eventos", font=ctk.CTkFont(size=15, weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def add_log(self, message):
        """ Adiciona uma mensagem ao Log de Eventos """
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end") # Auto-scroll

    def add_user(self):
        self.add_log("Botão 'Adicionar Usuário' clicado.")
        # Lógica a ser implementada no próximo passo

    def add_topic(self):
        self.add_log("Botão 'Adicionar Tópico' clicado.")
        # Lógica a ser implementada no próximo passo

if __name__ == "__main__":
    app = ManagerApp()
    app.mainloop()