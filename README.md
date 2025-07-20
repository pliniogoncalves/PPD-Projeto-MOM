# Projeto MOM: Sistema de Chat com Filas e Tópicos

Este projeto foi desenvolvido para a disciplina de Programação Paralela e Distribuída e implementa um sistema de comunicação baseado em Mensagens (Message-Oriented Middleware - MOM) utilizando o protocolo MQTT.

O sistema é composto por duas aplicações principais:
1.  **Gerenciador (`manager.py`):** Uma interface administrativa para criar e gerenciar usuários e tópicos de discussão, além de monitorar em tempo real a quantidade de mensagens privadas pendentes para cada usuário.
2.  **Usuário (`user.py`):** A aplicação de chat para o usuário final, permitindo o login, a inscrição em tópicos, o envio de mensagens para tópicos públicos e o envio de mensagens diretas (com suporte offline) para outros usuários.

---

## Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Comunicação:** Protocolo MQTT
* **Broker MQTT:** `broker.hivemq.com` (público)
* **Biblioteca MQTT:** `paho-mqtt`
* **Interface Gráfica (GUI):** `customtkinter`

---

## Funcionalidades Implementadas

### Gerenciador
* [x] Adicionar e listar usuários, com verificação de duplicidade.
* [x] Adicionar e listar tópicos, com verificação de duplicidade.
* [x] Criação automática de uma "fila" (tópico privado) para cada novo usuário.
* [x] Listar em tempo real a quantidade de mensagens pendentes nas filas de cada usuário.
* [x] Sincronização de estado (novos usuários e tópicos) com todos os clientes conectados usando a flag `retain` do MQTT.

### Usuário
* [x] Sistema de login com nome de usuário.
* [x] Permite assinar tópicos de interesse para receber mensagens.
* [x] Permite enviar mensagens para tópicos públicos.
* [x] Permite enviar mensagens diretas para outros usuários com suporte offline (usando a flag `retain`).
* [x] Sistema de confirmação de leitura (ACK) para o funcionamento do contador de mensagens pendentes.

---

## Como Configurar e Executar o Projeto

### 1. Pré-requisitos

* Python 3 instalado em sua máquina.
* Git (opcional, para clonar o repositório).

### 2. Instalação

Clone o repositório para a sua máquina local:
```bash
git clone https://github.com/pliniogoncalves/PPD-Projeto-MOM.git
cd PPD-Projeto-MOM
```

Instale as dependências necessárias a partir do arquivo `requirements.txt`. No terminal, execute:
```bash
# No Windows
py -m pip install -r requirements.txt

# No macOS/Linux
python3 -m pip install -r requirements.txt
```

### 3. Execução

Para testar o sistema, você precisa executar as duas aplicações simultaneamente. É recomendado abrir dois terminais separados na pasta do projeto.

**No Terminal 1 - Inicie o Gerenciador:**
```bash
py manager.py
```
* Uma janela de gerenciamento irá aparecer. Use-a para criar alguns usuários (ex: `ana`, `bruno`) e alguns tópicos (ex: `geral`, `devops`).

**No Terminal 2 - Inicie um Cliente de Usuário:**
```bash
py user.py
```
* Uma janela de login irá aparecer. Entre com um dos nomes de usuário que você criou (ex: `ana`).
* A tela principal do chat será carregada, já exibindo a lista de usuários e tópicos existentes.

**Para testar a comunicação, inicie um segundo cliente (opcional):**
* Abra um terceiro terminal e execute `py user.py` novamente.
* Faça login com o outro nome de usuário (ex: `bruno`).

### 4. Roteiro de Teste Sugerido

1.  **Mensagens em Tópico:**
    * Nas duas aplicações de usuário (`ana` e `bruno`), clique no botão do tópico `geral` para se inscrever.
    * Na tela de `ana`, envie uma mensagem para o tópico `geral`. A mensagem deve aparecer tanto na tela de `ana` quanto na de `bruno`.

2.  **Mensagens Diretas e Contagem:**
    * Na tela de `ana`, envie uma mensagem privada para `bruno`.
    * Observe o Gerenciador: o contador "Mensagens Pendentes" para `bruno` deve ir para `1`.
    * Observe a tela de `bruno`: a mensagem deve ser recebida.
    * Assim que a mensagem é recebida, observe o Gerenciador novamente: o contador de `bruno` deve voltar para `0`.

3.  **Mensagens Offline:**
    * Feche a aplicação do usuário `bruno`.
    * Na tela de `ana`, envie outra mensagem privada para `bruno`. O contador dele no Gerenciador irá para `1`.
    * Inicie a aplicação de `bruno` novamente e faça login. A mensagem pendente deve ser entregue imediatamente, e o contador no Gerenciador deve zerar.

## 🔁 Outras Versões do Projeto

Este repositório também contém implementações alternativas para estudo e comparação, disponíveis em branches separadas:

- **Versão RabbitMQ Pura:**

```bash
git checkout versao-rabbitmq
```

- **Versão MQTT-RabbitMQ (Hibrido das duas tecnologias):**

```bash
git checkout versao-mqtt-rabbitmq-hibrido
```