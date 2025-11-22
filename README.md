# Aetheris: Serverless C2 Framework

[![CI - Tests, Linter & Coverage](https://github.com/djalv/serverless-c2-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/djalv/serverless-c2-framework/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/djalv/serverless-c2-framework/graph/badge.svg)](https://codecov.io/gh/djalv/serverless-c2-framework)

---

### Nomes dos membros do grupo
* **Álvaro Cândido de Oliveira Neto**

---

### Breve explicação sobre o sistema

O **Aetheris** é um sistema de Comando e Controle (C2) desenvolvido com uma arquitetura **serverless** na AWS. O objetivo do sistema é simular uma infraestrutura ofensiva moderna de *Red Team*, focada em furtividade e resiliência.

Diferente de C2s tradicionais baseados em servidores fixos, o Aetheris utiliza componentes de nuvem efêmeros para gerenciar agentes comprometidos. O sistema é composto por três partes principais:
1.  **Agente:** Um script executado na máquina alvo que realiza check-ins periódicos, recebe comandos e exfiltra resultados.
2.  **Backend:** Uma API na AWS (API Gateway + Lambda) que gerencia a lógica de comunicação, armazena o estado no DynamoDB e guarda arquivos exfiltrados no S3.
3.  **Operador CLI:** Uma interface de linha de comando interativa que permite ao operador gerenciar múltiplos agentes e enviar tarefas em tempo real.

---

### Breve explicação sobre as tecnologias utilizadas

O projeto foi construído utilizando uma stack moderna de desenvolvimento e testes:

* **Linguagem:** Python 3.11+ para todos os componentes.
* **AWS Serverless:**
    * **AWS Lambda:** Execução da lógica de backend (Check-in e Armazenamento).
    * **Amazon DynamoDB:** Banco de dados NoSQL para persistência de estado.
    * **Amazon S3:** Armazenamento de objetos para resultados de comandos.
* **Infraestrutura como Código (IaC):** AWS SAM (Serverless Application Model) para definição e deploy da infraestrutura.
* **Interface CLI:** Bibliotecas `click` e `rich` para criar uma experiência de terminal interativa e visualmente rica.
* **Qualidade e Testes:**
    * **Pytest:** Framework principal de testes.
    * **Moto:** Biblioteca para simular (mockar) serviços da AWS inteiros em memória.
    * **Pytest-Cov:** Para mensuração de cobertura de código.
    * **GitHub Actions:** Pipeline de CI/CD para automação de testes em múltiplos sistemas operacionais (Linux, Windows, macOS).

---

### Como executar os testes localmente

Para validar o sistema e rodar a suíte de testes na sua máquina, siga as instruções abaixo.

#### 1. Configuração do Ambiente (Pré-requisitos)

Certifique-se de ter o **Python 3.11+**, **AWS CLI** e **AWS SAM CLI** instalados.

Clone o repositório e instale as dependências em um ambiente virtual isolado:

```bash
# 1. Clonar o repositório
git clone [https://github.com/djalv/serverless-c2-framework.git](https://github.com/djalv/serverless-c2-framework.git)
cd serverless-c2-framework

# 2. Criar e ativar o ambiente virtual
python3 -m venv .venv
source .venv/bin/activate  # No Windows use: .\.venv\Scripts\activate

# 3. Instalar dependências do projeto e de testes
pip install -r requirements-dev.txt
pip install -r src/agent/requirements.txt
pip install -r src/operator_cli/requirements.txt
```

#### 2. Executar Testes de Unidade

Estes testes validam a lógica interna de cada módulo (`agent`, `backend`, `cli`) utilizando Mocks. Eles são rápidos e não exigem conexão com a AWS, pois utilizam a biblioteca moto para simular a nuvem.

```bash
pytest tests/unit/
```

#### 3. Executar Testes de Integração e E2E

Estes testes validam o fluxo completo do sistema conectando-se à infraestrutura real na AWS. Nota: Requer uma conta AWS configurada com `aws configure` e o deploy da infraestrutura realizado.

##### Passo A: Fazer o Deploy (apenas na primeira vez)

```bash
sam build -t iac/template.yaml
sam deploy --guided
```

Anote a URL da API (CheckInApiUrl) exibida nos "Outputs" ao final do deploy.

##### Passo B: Configurar Variáveis e Rodar

###### 1. Crie um arquivo .env na raiz do projeto com a URL da sua API:

```bash
API_ENDPOINT_URL="https://xxxxxx.execute-api.us-east-1.amazonaws.com/Prod/checkin/"
```

###### 2. Execute os testes:

```bash
pytest tests/integration/ tests/e2e/
```

#### 4. Gerar Relatório de Cobertura

Para medir a cobertura dos testes (incluindo cobertura de branches) e visualizar o relatório no terminal:

```bash
pytest --cov=src --cov-branch --cov-report=term-missing
```

### Como Executar a Ferramenta (Uso Manual)

#### 1. Iniciar o Agente
Em um terminal (na máquina alvo ou localmente para teste):

```bash
# Executar como módulo para garantir imports corretos
python -m src.agent.main
```

#### 2. Iniciar a CLI do Operador
Em outro terminal:

```bash
python -m src.operator_cli.operator_cli
```

Dentro da CLI Interativa:

* `agents`: Lista os agentes ativos.

* `select <AGENT_ID>`: Seleciona um agente para interagir.

* `run <COMANDO>`: Envia um comando para o agente selecionado e aguarda o resultado (ex: run whoami).

* `exit`: Sai da CLI.
