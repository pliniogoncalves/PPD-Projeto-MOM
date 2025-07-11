import customtkinter as ctk
from tkinter import messagebox
import os
import queue
from rabbitmq_client import RabbitMQClient
from mqtt_client import MQTTClient

UNIQUE_PREFIX = "ppd-hibrido-final/"
USUARIOS_FILE = "usuarios_hibrido.txt"
TOPICOS_FILE = "topicos_hibrido.txt"
TOPIC_MGMT_USERS = f"{UNIQUE_PREFIX}sistema/gerenciamento/usuarios"
TOPIC_MGMT_TOPICS = f"{UNIQUE_PREFIX}sistema/gerenciamento/topicos"
TOPIC_AUTH_REQUEST = f"{UNIQUE_PREFIX}sistema/auth/request"
TOPIC_PRESENCE = f"{UNIQUE_PREFIX}sistema/presenca"
COLOR_ONLINE = "#1F6AA5"
COLOR_OFFLINE = "#C21807"

def ler_arquivo(arquivo):
    if not os.path.exists(arquivo): return []
    with open(arquivo, "r") as f:
        return [linha.strip() for linha in f if linha.strip()]

def salvar_em_arquivo(arquivo, nome):
    with open(arquivo, "a") as f:
        f.write(nome + "\n")

def remover_de_arquivo(arquivo, nome_para_remover):
    linhas = ler_arquivo(arquivo)
    with open(arquivo, "w") as f:
        for linha in linhas:
            if linha != nome_para_remover:
                f.write(linha + "\n")

class ManagerHibridoApp(ctk.CTk):
    def __init__(self, rabbit_client):
        super().__init__()
        self.rabbit_client = rabbit_client
        self.user_status = {}
        self.gui_queue = queue.Queue()

        self.title("Gerenciador Híbrido (FINAL)")
        self.geometry("800x600")
        
        self.mqtt_client = MQTTClient(broker_address="broker.hivemq.com", on_message_callback=self.on_mqtt_message)
        if not self.mqtt_client.connect():
            self.show_error_and_exit("Não foi possível conectar ao broker MQTT.")
            return

        self.create_widgets()
        self.mqtt_client.subscribe(TOPIC_AUTH_REQUEST)
        self.mqtt_client.subscribe(f"{TOPIC_MGMT_USERS}/+")
        self.mqtt_client.subscribe(f"{TOPIC_MGMT_TOPICS}/+")
        self.mqtt_client.subscribe(TOPIC_PRESENCE)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.add_log("Gerenciador Híbrido iniciado.")
        self.update_all_lists()
        self.process_gui_queue()
        self.periodic_check_queues()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1); self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1); self.grid_rowconfigure(1, weight=1)
        user_frame = ctk.CTkFrame(self)
        user_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        user_frame.grid_columnconfigure(0, weight=1); user_frame.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(user_frame, text="Gerenciar Usuários", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.user_entry = ctk.CTkEntry(user_frame, placeholder_text="Nome do usuário")
        self.user_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkButton(user_frame, text="Adicionar Usuário", command=self.add_user).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.user_list_frame = ctk.CTkScrollableFrame(user_frame, label_text="Usuários do Sistema")
        self.user_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        topic_frame = ctk.CTkFrame(self)
        topic_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        topic_frame.grid_columnconfigure(0, weight=1); topic_frame.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(topic_frame, text="Gerenciar Tópicos", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.topic_entry = ctk.CTkEntry(topic_frame, placeholder_text="Nome do tópico")
        self.topic_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        ctk.CTkButton(topic_frame, text="Adicionar Tópico", command=self.add_topic).grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        self.topic_list_frame = ctk.CTkScrollableFrame(topic_frame, label_text="Tópicos Oficiais")
        self.topic_list_frame.grid(row=3, column=0, padx=10, pady=(0,10), sticky="nsew")
        counts_frame = ctk.CTkFrame(self)
        counts_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        counts_frame.grid_columnconfigure(0, weight=1); counts_frame.grid_rowconfigure(0, weight=1)
        ctk.CTkLabel(counts_frame, text="Mensagens Pendentes (RabbitMQ)", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.counts_display_frame = ctk.CTkScrollableFrame(counts_frame)
        self.counts_display_frame.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")
        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1); log_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, text="Log de Eventos", font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=10, pady=10)
        self.log_textbox = ctk.CTkTextbox(log_frame, state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, padx=10, pady=(0,10), sticky="nsew")

    def add_log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", f"- {message}\n")
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
        
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

    def handle_mqtt_message(self, topic, payload):
        if topic == TOPIC_AUTH_REQUEST: self.handle_auth_request(payload)
        elif topic == TOPIC_PRESENCE: self.handle_presence_update(payload)
        elif topic.startswith(TOPIC_MGMT_USERS): self.handle_user_sync(topic, payload)
        elif topic.startswith(TOPIC_MGMT_TOPICS): self.handle_topic_sync(topic, payload)
            
    def handle_auth_request(self, payload):
        try:
            user_to_check, response_topic = payload.split(";")
            if user_to_check in ler_arquivo(USUARIOS_FILE):
                self.mqtt_client.publish(response_topic, "VALIDO")
                self.add_log(f"AUTH: Login para '{user_to_check}' validado.")
            else:
                self.mqtt_client.publish(response_topic, "INVALIDO")
                self.add_log(f"AUTH: Login para '{user_to_check}' negado.")
        except ValueError: self.add_log("AUTH: Requisição mal formatada.")

    def handle_presence_update(self, payload):
        try:
            user_name, status = payload.split(":")
            if user_name in ler_arquivo(USUARIOS_FILE):
                self.user_status[user_name] = status
                self.add_log(f"PRESENÇA: {user_name} está {status}")
                self.update_user_list_display()
        except ValueError: pass
    
    def handle_user_sync(self, topic, payload):
        self.update_user_list_display()

    def handle_topic_sync(self, topic, payload):
        self.update_topic_list_display()

    def add_user(self):
        user_name = self.user_entry.get().strip()
        if not user_name: return
        if user_name in ler_arquivo(USUARIOS_FILE):
            self.add_log(f"ERRO: Usuário '{user_name}' já existe.")
            return
        try:
            self.rabbit_client.declare_queue(f"queue_{user_name}")
            salvar_em_arquivo(USUARIOS_FILE, user_name)
            self.mqtt_client.publish(f"{TOPIC_MGMT_USERS}/{user_name}", "ADD", retain=True)
            self.update_user_list_display()
            self.user_entry.delete(0, ctk.END)
            self.add_log(f"Usuário '{user_name}' criado com sucesso.")
        except Exception as e: self.add_log(f"ERRO ao criar usuário '{user_name}': {e}")
            
    def remove_user(self, user_name):
        try:
            self.rabbit_client.delete_queue(f"queue_{user_name}")
            remover_de_arquivo(USUARIOS_FILE, user_name)
            self.mqtt_client.publish(f"{TOPIC_MGMT_USERS}/{user_name}", "", retain=True)
            self.mqtt_client.publish(TOPIC_PRESENCE, f"{user_name}:OFFLINE", retain=True)
            self.update_user_list_display()
            self.add_log(f"Usuário '{user_name}' removido com sucesso.")
        except Exception as e: self.add_log(f"ERRO ao remover '{user_name}': {e}")
            
    def add_topic(self):
        topic_name = self.topic_entry.get().strip()
        if not topic_name: return
        if topic_name in ler_arquivo(TOPICOS_FILE):
            self.add_log(f"ERRO: Tópico '{topic_name}' já existe.")
            return
        salvar_em_arquivo(TOPICOS_FILE, topic_name)
        self.mqtt_client.publish(f"{TOPIC_MGMT_TOPICS}/{topic_name}", "ADD", retain=True)
        self.update_topic_list_display()
        self.topic_entry.delete(0, ctk.END)
        self.add_log(f"Tópico '{topic_name}' criado com sucesso.")

    def remove_topic(self, topic_name):
        remover_de_arquivo(TOPICOS_FILE, topic_name)
        self.mqtt_client.publish(f"{TOPIC_MGMT_TOPICS}/{topic_name}", "", retain=True)
        self.update_topic_list_display()
        self.add_log(f"Tópico '{topic_name}' removido com sucesso.")

    def periodic_check_queues(self):
        self.check_all_queues()
        self.after(5000, self.periodic_check_queues)

    def check_all_queues(self):
        for widget in self.counts_display_frame.winfo_children(): widget.destroy()
        for user in ler_arquivo(USUARIOS_FILE):
            count = self.rabbit_client.get_message_count(f"queue_{user}")
            label = ctk.CTkLabel(self.counts_display_frame, text=f"Fila '{user}': {count} mensagens")
            label.pack(anchor="w", padx=10)

    def update_all_lists(self):
        self.update_user_list_display()
        self.update_topic_list_display()

    def update_user_list_display(self):
        for widget in self.user_list_frame.winfo_children(): widget.destroy()
        all_users = ler_arquivo(USUARIOS_FILE)
        online_users = [u for u in all_users if self.user_status.get(u) == "ONLINE"]
        offline_users = [u for u in all_users if self.user_status.get(u) != "ONLINE"]
        if online_users:
            header = ctk.CTkLabel(self.user_list_frame, text=f"Online ({len(online_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(5, 2))
            for user_name in sorted(online_users): self.create_user_list_item(user_name, True)
        if offline_users:
            header = ctk.CTkLabel(self.user_list_frame, text=f"Offline ({len(offline_users)})", font=ctk.CTkFont(weight="bold"))
            header.pack(anchor="w", padx=5, pady=(10, 2))
            for user_name in sorted(offline_users): self.create_user_list_item(user_name, False)
                
    def create_user_list_item(self, user_name, is_online):
        color = COLOR_ONLINE if is_online else COLOR_OFFLINE
        frame = ctk.CTkFrame(self.user_list_frame)
        frame.pack(fill="x", padx=5, pady=2)
        frame.grid_columnconfigure(1, weight=1)
        dot = ctk.CTkLabel(frame, text="●", text_color=color, font=ctk.CTkFont(size=18))
        dot.grid(row=0, column=0, sticky="w", padx=(5,2))
        label = ctk.CTkLabel(frame, text=user_name, anchor="w")
        label.grid(row=0, column=1, sticky="ew")
        button = ctk.CTkButton(frame, text="Remover", width=80, command=lambda u=user_name: self.remove_user(u))
        button.grid(row=0, column=2, padx=5)

    def update_topic_list_display(self):
        for widget in self.topic_list_frame.winfo_children(): widget.destroy()
        for topic_name in ler_arquivo(TOPICOS_FILE):
            frame = ctk.CTkFrame(self.topic_list_frame)
            frame.pack(fill="x", padx=5, pady=2)
            frame.grid_columnconfigure(0, weight=1)
            label = ctk.CTkLabel(frame, text=topic_name, anchor="w")
            label.grid(row=0, column=0, sticky="ew")
            button = ctk.CTkButton(frame, text="Remover", width=80, command=lambda t=topic_name: self.remove_topic(t))
            button.grid(row=0, column=2, padx=5)

    def on_closing(self):
        if self.rabbit_client: self.rabbit_client.close()
        if self.mqtt_client: self.mqtt_client.disconnect()
        self.destroy()
        
    def show_error_and_exit(self, error_message):
        messagebox.showerror("Erro Crítico", error_message)
        self.destroy()

if __name__ == "__main__":
    try:
        rabbit_client = RabbitMQClient()
        app = ManagerHibridoApp(rabbit_client)
        app.mainloop()
    except Exception as e: messagebox.showerror("Erro Crítico", f"Falha ao iniciar o Gerenciador Híbrido.\n{e}")