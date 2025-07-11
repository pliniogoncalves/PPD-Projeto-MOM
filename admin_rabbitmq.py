import customtkinter as ctk
from tkinter import messagebox
from rabbitmq_client import RabbitMQClient

class AdminApp(ctk.CTk):
    def __init__(self, client):
        super().__init__()
        self.client = client

        # --- Configuração da Janela Principal ---
        self.title("Gerenciador MOM (RabbitMQ)")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Listas em memória para a sessão atual ---
        self.users = []
        self.topics = []
        
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
        self.user_list_frame = ctk.CTkScrollableFrame(user_frame, label_text="Usuários (Sessão Atual)")
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
        self.topic_list_frame = ctk.CTkScrollableFrame(topic_frame, label_text="Tópicos (Sessão Atual)")
        self.topic_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        topic_frame.grid_rowconfigure(3, weight=1)

        # --- Frame de Mensagens Pendentes ---
        counts_frame = ctk.CTkFrame(self)
        counts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        counts_frame.grid_columnconfigure(0, weight=1); counts_frame.grid_rowconfigure(1, weight=1)
        counts_label = ctk.CTkLabel(counts_frame, text="Mensagens Pendentes por Usuário", font=ctk.CTkFont(size=15, weight="bold"))
        counts_label.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.counts_display_frame = ctk.CTkScrollableFrame(counts_frame)
        self.counts_display_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        check_button = ctk.CTkButton(counts_frame, text="Verificar Agora", command=self.check_all_queues)
        check_button.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        # --- Frame de Log de Eventos ---
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1); log_frame.grid_rowconfigure(1, weight=1)
        log_label = ctk.CTkLabel(log_frame, text="Log de Eventos", font=ctk.CTkFont(size=15, weight="bold"))
        log_label.grid(row=0, column=0, padx=10, pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def add_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"- {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def add_user(self):
        user_name = self.user_entry.get().strip()
        if not user_name: return
        if user_name in self.users:
            self.add_log(f"ERRO: Usuário '{user_name}' já adicionado nesta sessão.")
            return
        try:
            queue_name = f"queue_{user_name}"
            self.client.declare_queue(queue_name)
            self.users.append(user_name)
            self.update_user_list()
            self.user_entry.delete(0, ctk.END)
            self.add_log(f"Usuário '{user_name}' e fila '{queue_name}' criados no broker.")
        except Exception as e:
            self.add_log(f"ERRO ao criar usuário: {e}")

    def remove_user(self, user_name):
        try:
            queue_name = f"queue_{user_name}"
            self.client.delete_queue(queue_name)
            self.users.remove(user_name)
            self.update_user_list()
            self.check_all_queues() # Atualiza a lista de contagem
            self.add_log(f"Usuário '{user_name}' e fila removidos do broker.")
        except Exception as e:
            self.add_log(f"ERRO ao remover usuário: {e}")

    def add_topic(self):
        topic_name = self.topic_entry.get().strip()
        if not topic_name: return
        if topic_name in self.topics:
            self.add_log(f"ERRO: Tópico '{topic_name}' já adicionado nesta sessão.")
            return
        try:
            self.client.declare_exchange(topic_name, 'fanout')
            self.topics.append(topic_name)
            self.update_topic_list()
            self.topic_entry.delete(0, ctk.END)
            self.add_log(f"Tópico (exchange) '{topic_name}' criado no broker.")
        except Exception as e:
            self.add_log(f"ERRO ao criar tópico: {e}")

    def remove_topic(self, topic_name):
        try:
            self.client.delete_exchange(topic_name)
            self.topics.remove(topic_name)
            self.update_topic_list()
            self.add_log(f"Tópico '{topic_name}' removido do broker.")
        except Exception as e:
            self.add_log(f"ERRO ao remover tópico: {e}")

    def update_user_list(self):
        for widget in self.user_list_frame.winfo_children(): widget.destroy()
        for user_name in self.users:
            frame = ctk.CTkFrame(self.user_list_frame)
            frame.pack(fill="x", padx=5, pady=2)
            frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(frame, text=user_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=5)
            button = ctk.CTkButton(frame, text="Remover", width=80, command=lambda u=user_name: self.remove_user(u))
            button.grid(row=0, column=1, padx=5)

    def update_topic_list(self):
        for widget in self.topic_list_frame.winfo_children(): widget.destroy()
        for topic_name in self.topics:
            frame = ctk.CTkFrame(self.topic_list_frame)
            frame.pack(fill="x", padx=5, pady=2)
            frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(frame, text=topic_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew", padx=5)
            button = ctk.CTkButton(frame, text="Remover", width=80, command=lambda t=topic_name: self.remove_topic(t))
            button.grid(row=0, column=1, padx=5)
            
    def check_all_queues(self):
        self.add_log("Verificando contagem de mensagens...")
        for widget in self.counts_display_frame.winfo_children(): widget.destroy()
        
        # Verifica as filas dos usuários criados nesta sessão
        for user in self.users:
            queue_name = f"queue_{user}"
            count = self.client.get_message_count(queue_name)
            label_text = f"Fila '{queue_name}': {count} mensagens"
            label = ctk.CTkLabel(self.counts_display_frame, text=label_text)
            label.pack(anchor="w", padx=10)
        self.add_log("Verificação concluída.")
        
    def on_closing(self):
        self.client.close()
        self.destroy()

if __name__ == "__main__":
    try:
        client = RabbitMQClient()
        app = AdminApp(client)
        app.protocol("WM_DELETE_WINDOW", app.on_closing)
        app.mainloop()
    except Exception as e:
        # Fallback para exibir erro se a conexão inicial falhar
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror("Erro Crítico de Conexão", f"Não foi possível conectar ao RabbitMQ.\nVerifique se o servidor está rodando.\n\nDetalhes: {e}", parent=root)