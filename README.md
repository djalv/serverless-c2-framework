# Projeto de Teste de Software: Serverless C2 Framework

O projeto consiste no desenvolvimento e teste de um C2 (Command & Control) Framework utilizando uma arquitetura serverless na nuvem AWS.

---

### 1. Membros
* **Álvaro Cândido de Oliveira Neto**

---

### 2. Descrição

O projeto propõe a construção de um C2 Framework, uma ferramenta essencial em operações de Red Team para simulação de adversários. Diferente de arquiteturas tradicionais que dependem de um servidor monolítico e sempre ativo, este projeto adota uma abordagem **serverless** (Funções como Serviço).

O objetivo é criar uma infraestrutura de comando e controle que seja resiliente, escalável, de baixo custo e, principalmente, discreta (*stealth*), dificultando sua detecção e rastreamento.

#### Fluxo de Funcionamento

O sistema é distribuído e orientado a eventos, composto pelos seguintes fluxos principais:

1.  **Check-in do Agente:** Um "agente" em uma máquina comprometida se comunica periodicamente com um endpoint de API, que invoca uma função serverless. A função registra a atividade do agente e verifica por novas tarefas em um banco de dados.
2.  **Atribuição de Tarefas:** O "operador" utiliza uma interface de linha de comando para registrar novas tarefas para um agente específico no banco de dados.
3.  **Execução e Coleta de Resultados:** No próximo check-in, o agente recebe a tarefa, executa o comando e envia o resultado para um segundo endpoint de API. Este, por sua vez, aciona outra função Lambda que armazena a saída em um serviço de armazenamento de objetos.

---

### 3. Possíveis Tecnologias

* #### Nuvem (Cloud - AWS)
    * **AWS Lambda:** Para a execução do código do backend sem a necessidade de gerenciar servidores.
    * **AWS API Gateway:** Para criar e gerenciar os endpoints HTTP que servirão como porta de entrada para a comunicação com os agentes.
    * **AWS DynamoDB:** Como banco de dados NoSQL para gerenciar o estado dos agentes e a fila de tarefas de forma rápida e escalável.
    * **AWS S3 (Simple Storage Service):** Para o armazenamento dos resultados dos comandos executados, ideal para saídas de texto ou binários.
    * **AWS IAM (Identity and Access Management):** Para o gerenciamento fino de permissões entre os serviços, um pilar de segurança da arquitetura.

* #### Linguagem e Ferramentas
    * **Python 3.x**: Linguagem principal para o desenvolvimento do backend, do agente e da CLI.
    * **Boto3**: O SDK oficial da AWS para Python, utilizado para a comunicação entre os componentes e os serviços da AWS
    * **Requests**: Biblioteca padrão para a realização de chamadas HTTP do agente para o API Gateway.

* #### Infraestrutura como Código (IaC)
    * **AWS SAM (Serverless Application Model) ou Terraform:** Será explorado o uso de IaC para provisionar e gerenciar a infraestrutura na nuvem de forma automatizada e repetível.