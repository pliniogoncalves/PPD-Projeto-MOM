# Projeto MOM: Sistema de Mensageria Híbrido (MQTT + RabbitMQ)

Esta é a implementação avançada de um Message-Oriented Middleware (MOM) que utiliza uma **arquitetura híbrida**, combinando **MQTT** e **RabbitMQ** para alavancar os pontos fortes de cada tecnologia.

O sistema é composto por duas aplicações principais que se conectam a ambos os brokers para criar uma solução robusta e em tempo real.

## 🚧 Tecnologias Utilizadas

- 🐍 **Python 3**
- 🔌 **Arquitetura Híbrida:**
  - **MQTT (com `paho-mqtt`)**: Utilizado para todas as comunicações leves e em tempo real, como o sistema de **presença (online/offline)** e o **chat em tópicos públicos**. Sua eficiência em pub/sub e o recurso de *Last Will and Testament* são ideais para isso.
  - **RabbitMQ (com `pika`)**: Utilizado como um backend robusto para garantir a entrega de **múltiplas mensagens offline** através de suas filas duráveis nativas.
- 🎨 **CustomTkinter** (para GUI Moderna)

## ✅ Funcionalidades Implementadas

O sistema cumpre todos os requisitos do projeto, utilizando a melhor ferramenta para cada cenário:

### 👨‍💼 Gerenciador
- Cria e remove usuários e tópicos.
- Interage com ambos os brokers para gerenciar filas (RabbitMQ) e anunciar o estado dos usuários (MQTT).

### 👤 Usuário
- Login com validação.
- Participação em chats em tópicos públicos (via MQTT).
- Visualização em tempo real do status online/offline de outros usuários (via MQTT).
- Envio de mensagens diretas:
  - Se o destinatário estiver **online**: mensagem em tempo real via MQTT.
  - Se o destinatário estiver **offline**: mensagem é **enfileirada no RabbitMQ**.
- Ao se reconectar, o usuário recebe um **histórico completo** de mensagens offline armazenadas (via RabbitMQ).

---

## 🚀 Como Rodar o Projeto

### 1. Pré-requisitos

- Python 3.7+
- Servidor **RabbitMQ** instalado e em execução localmente.
- Conexão com a internet (para uso do broker MQTT público).

### 2. Instalação

```bash
# Clone o repositório
git clone https://github.com/pliniogoncalves/PPD-Projeto-MOM.git
cd PPD-Projeto-MOM

# Garanta que você está na branch principal
git checkout main

# Instale as dependências
py -m pip install -r requirements.txt
```

### 3. Inicie o Servidor RabbitMQ

Certifique-se de que o RabbitMQ esteja ativo localmente.

No Windows, pode iniciar pelo menu ou pelo terminal:
```
rabbitmq-server start
```

### 4. Execute as Aplicações

Abra dois ou mais terminais na pasta do projeto.

**Terminal 1 - Gerenciador:**

```bash
python manager_hibrido.py
```

**Terminais adicionais - Usuários:**

```bash
python user_hibrido.py
```

---

## 🔁 Outras Versões do Projeto

Este repositório também contém implementações alternativas para estudo e comparação, disponíveis em branches separadas:

- **Versão MQTT Pura:**

```bash
git checkout versao-mqtt
```

- **Versão RabbitMQ Pura:**

```bash
git checkout versao-rabbitmq
```

---

