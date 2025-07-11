# Projeto MOM - Sistema de Mensageria Distribuída (Versão RabbitMQ)

Esta é a implementação de um Message-Oriented Middleware (MOM) que utiliza **RabbitMQ** como broker de mensagens e **CustomTkinter** para as interfaces gráficas. O sistema permite o gerenciamento centralizado de usuários e tópicos, e a comunicação em tempo real entre os usuários, incluindo suporte a múltiplas mensagens offline.

## Tecnologias Utilizadas
- 🐍 Python 3
- 🐇 **RabbitMQ** (Broker de Mensagens)
- 🎨 **CustomTkinter** (GUI Moderna)
- 📬 **Pika** (Cliente RabbitMQ para Python)

## Arquitetura e Funcionalidades

Este projeto é dividido em dois componentes principais:

1.  **Gerenciador (`admin_rabbitmq.py`):**
    * Uma aplicação central para o administrador do sistema.
    * Cria e remove **filas de usuários** e **tópicos (exchanges)** no broker RabbitMQ.
    * Lista as entidades cadastradas.
    * Monitora a **quantidade de mensagens pendentes** em cada fila de usuário, consultando o broker diretamente.
    * Valida tentativas de login, garantindo que apenas usuários cadastrados possam entrar no sistema.

2.  **Aplicação de Usuário (`user_rabbitmq.py`):**
    * Interface para o usuário final.
    * Requer validação de login contra o Gerenciador.
    * Permite se inscrever e cancelar a inscrição em múltiplos tópicos.
    * Envia e recebe mensagens em tópicos públicos.
    * Envia mensagens diretas para outros usuários.
    * Recebe **múltiplas mensagens offline** que foram armazenadas em sua fila pessoal no RabbitMQ.

## 🚀 Como Rodar o Projeto

### 1. Pré-requisitos
- Python 3.7+
- **Servidor RabbitMQ instalado e rodando localmente.** (Você pode baixá-lo em [rabbitmq.com](https://www.rabbitmq.com/download.html))

### 2. Clone o Repositório e Instale as Dependências

```bash
# Clone o repositório (se ainda não o fez)
git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
cd seu-repositorio

# Certifique-se de estar na branch correta
git checkout versao-rabbitmq

# Instale as dependências
pip install -r requirements.txt

```

### 3. Inicie o Servidor RabbitMQ

Antes de executar os scripts Python, garanta que o seu servidor RabbitMQ local esteja no ar. Geralmente, isso é feito através do menu Iniciar ou executando rabbitmq-server no terminal apropriado.

### 4. Execute as Aplicações
Abra dois ou mais terminais na pasta do projeto.

```bash

# No Terminal 1 (O Gerenciador):

python admin_rabbitmq.py

#Nos outros Terminais (Os Usuários):

python user_rabbitmq.py