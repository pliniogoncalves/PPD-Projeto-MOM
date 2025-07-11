import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import threading
import datetime
from rabbitmq_client import RabbitMQClient

TOPICOS_FILE = "topicos_rabbit.txt"
USUARIOS_FILE = "usuarios_rabbit.txt"
COLOR_SUBSCRIBED = ("#4A4A4A", "#555555")

def ler_arquivo(arquivo):
    if not os.path.exists(arquivo): return []
    with open(arquivo, "r") as f:
        return [linha.strip() for linha in f if linha.strip()]

class UserApp(ctk.CTk):
    def __init__(self, client):
        super().__init__()
        self.client = client
        self.title("Aplicação de Usuário (RabbitMQ)")
        self.geometry("400x250")
        
        self.user_name = None
        self.subscribed_topics = set()

        self.create_login_widgets()

    def create_login_widgets(self):
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(padx=20, pady=20, fill="both", expand=True)
        label = ctk.CTkLabel(self.login_frame, text="Digite seu nome de usuário:", font=ctk.CTkFont(size=15))
        label.pack(pady=10)
        self.username_entry = ctk.CTkEntry(self.login_frame, width=200)
        self.username_entry.pack(pady=10)
        self.login_button = ctk.CTkButton(self.login_frame, text="Entrar", command=self.login)
        self.login_button.pack(pady=20)
        self.status_label = ctk.CTkLabel(self.login_frame, text="")
        self.status_label.pack(pady=(0, 10))
        self.username_entry.bind("<Return>", lambda event: self.login())

    def login(self):
        self.user_name = self.username_entry.get().strip()
        if not self.user_name:
            self.status_label.configure(text="Nome não pode ser vazio.", text_color="red")
            return
        
        if self.user_name not in ler_arquivo(USUARIOS_FILE):
            self.status_label.configure(text="Usuário não cadastrado pelo admin.", text_color="red")
            return
            
        self.login_frame.destroy()
        self.geometry("900x700")
        self.title(f"MOM - Usuário: {self.user_name} (RabbitMQ)")
        self.setup_main_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.start_consuming_direct_messages()
        self.update_lists()

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
        
        self.topic_combobox = ctk.CTkComboBox(right_frame, values=[])
        self.topic_combobox.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        self.topic_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o tópico")
        self.topic_msg_entry.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        send_topic_button = ctk.CTkButton(right_frame, text="Enviar para Tópico", command=self.send_to_topic)
        send_topic_button.grid(row=3, column=0, padx=10, pady=10, sticky="ew")
        
        self.user_combobox = ctk.CTkComboBox(right_frame, values=[])
        self.user_combobox.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.user_msg_entry = ctk.CTkEntry(right_frame, placeholder_text="Mensagem para o usuário")
        self.user_msg_entry.grid(row=2, column=1, sticky="ew", padx=10, pady=5)
        send_user_button = ctk.CTkButton(right_frame, text="Enviar para Usuário", command=self.send_to_user)
        send_user_button.grid(row=3, column=1, sticky="ew", padx=10, pady=10)

    def update_lists(self):
        for widget in self.topics_list_frame.winfo_children(): widget.destroy()
        all_topics = ler_arquivo(TOPICOS_FILE)
        for topic_name in sorted(all_topics):
            is_subscribed = topic_name in self.subscribed_topics
            btn_text = f"{topic_name} (Sair)" if is_subscribed else topic_name
            btn_color = COLOR_SUBSCRIBED if is_subscribed else ("#3B8ED0", "#1F6AA5")
            btn_command = lambda t=topic_name, sub=is_subscribed: self.unsubscribe_from_topic(t) if sub else self.subscribe_to_topic(t)
            btn = ctk.CTkButton(self.topics_list_frame, text=btn_text, command=btn_command, fg_color=btn_color)
            btn.pack(padx=10, pady=5, fill="x")

        for widget in self.users_list_frame.winfo_children(): widget.destroy()
        all_users = [u for u in ler_arquivo(USUARIOS_FILE) if u != self.user_name]
        for user_name in sorted(all_users):
            label = ctk.CTkLabel(self.users_list_frame, text=f"● {user_name}", text_color=("#1F6AA5", "#1F6AA5"))
            label.pack(padx=10, pady=5, anchor="w")

        subscribed_list = sorted(list(self.subscribed_topics))
        self.topic_combobox.configure(values=subscribed_list)
        if self.topic_combobox.get() not in subscribed_list:
            self.topic_combobox.set(subscribed_list[0] if subscribed_list else "")

        self.user_combobox.configure(values=all_users)
        if self.user_combobox.get() not in all_users:
            self.user_combobox.set(all_users[0] if all_users else "")
            
        self.after(5000, self.update_lists)

    def add_log(self, message):
        self.after(0, self._add_log_thread_safe, message)

    def _add_log_thread_safe(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"[{timestamp}] {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def subscribe_to_topic(self, topic_name):
        if topic_name not in self.subscribed_topics:
            self.subscribed_topics.add(topic_name)
            self.client.start_consuming_from_exchange(topic_name, self.on_topic_message)
            self.add_log(f"Inscrito no tópico: {topic_name}")
            self.update_lists()
    
    def unsubscribe_from_topic(self, topic_name):
        if topic_name in self.subscribed_topics:
            self.subscribed_topics.remove(topic_name)
            self.add_log(f"Inscrição para '{topic_name}' será ignorada. (Reinicie para parar o consumo)")
            self.update_lists()
            
    def start_consuming_direct_messages(self):
        queue_name = f"queue_{self.user_name}"
        self.client.start_consuming_from_queue(queue_name, self.on_direct_message)
        self.add_log(f"Ouvindo por mensagens diretas na fila: {queue_name}")

    def on_direct_message(self, ch, method, properties, body):
        self.add_log(f"[Mensagem Direta] {body.decode()}")

    def on_topic_message(self, ch, method, properties, body):
        topic_name = method.exchange
        self.add_log(f"[{topic_name}] {body.decode()}")

    def send_to_topic(self):
        topic_name = self.topic_combobox.get()
        message = self.topic_msg_entry.get().strip()
        if not topic_name or not message: return
        self.client.publish_to_exchange(topic_name, f"({self.user_name}) {message}")
        self.add_log(f"Você para ({topic_name}): {message}")
        self.topic_msg_entry.delete(0, ctk.END)

    def send_to_user(self):
        recipient = self.user_combobox.get()
        message = self.user_msg_entry.get().strip()
        if not recipient or not message: return
        queue_name = f"queue_{recipient}"
        self.client.publish_to_queue(queue_name, f"de {self.user_name}: {message}")
        self.add_log(f"Você para {recipient} (Privado): {message}")
        self.user_msg_entry.delete(0, ctk.END)

    def on_closing(self):
        self.client.close()
        self.destroy()

if __name__ == "__main__":
    try:
        client = RabbitMQClient()
        app = UserApp(client)
        app.mainloop()
    except Exception as e:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Erro Crítico", f"Não foi possível iniciar a aplicação.\nVerifique se o RabbitMQ está rodando.\n\nDetalhes: {e}")