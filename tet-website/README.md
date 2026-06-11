# TET Website - Transparency Evaluation Tool for Software Ecosystems

## 📋 Visão Geral

O **TET Website** é uma aplicação web desenvolvida em Flask que faz parte do framework SECO-TransP. Este sistema permite que gestores de ecossistemas de software avaliem e monitorem a transparência de seus portais através de uma interface intuitiva, coletando dados multimodais e gerando dashboards analíticos para tomada de decisão.

## 🚀 Principais Funcionalidades

### Para Gestores de SECO
- **Gerenciamento de Avaliações**: Criação e configuração de avaliações personalizadas
- **Dashboards Analíticos**: Visualização de resultados através de heatmaps, gráficos e métricas

## 🛠 Tecnologias Utilizadas

### Backend
- **Python 3.10+**: Linguagem principal
- **Flask 3.1.0**: Framework web
- **SQLAlchemy 2.0.38**: ORM para banco de dados
- **Flask-Migrate 4.1.0**: Migrações de banco de dados
- **Alembic 1.15.1**: Versionamento de esquema de banco
- **bcrypt 4.3.0**: Criptografia de senhas

### Frontend
- **HTML5/CSS3**: Estrutura e estilização
- **JavaScript (ES6+)**: Interatividade e lógica frontend
- **Jinja2 3.1.5**: Template engine
- **Chart.js**: Visualização de dados
- **Bootstrap**: Framework CSS responsivo

### Banco de Dados
- **MySQL**: Sistema de gerenciamento de banco de dados relacional
- **mysql-connector-python 9.2.0**: Conector Python para MySQL

### Segurança e Autenticação
- **Flask-Caching 2.3.1**: Sistema de cache
- **python-dotenv 1.1.0**: Gerenciamento de variáveis de ambiente
- **Verificação de Email**: Sistema de confirmação de cadastro
- **Reset de Senha**: Recuperação segura de conta

### Integrações
- **Flask-CORS 5.0.1**: Suporte para Cross-Origin Resource Sharing
- **UX-Tracking**: Integração opcional para captura de interações (API externa)
- **Chrome Extension**: Integração com extensão do navegador

## 📁 Estrutura do Projeto

```
tet-website/
├── app.py                      # Inicialização da aplicação Flask
├── database.py                 # Configuração do banco de dados
├── functions.py                # Funções auxiliares
├── requirements.txt            # Dependências Python
│
├── models/                     # Modelos ORM (SQLAlchemy)
│   ├── __init__.py
│   ├── collection_data.py     # Dados coletados das avaliações
│   ├── database.py             # Inicialização do banco
│   ├── enums.py                # Enumerações do sistema
│   ├── evaluation.py           # Modelo de avaliação
│   ├── guideline.py            # Guidelines e critérios
│   ├── questionnaire.py        # Questionários
│   ├── task.py                 # Tarefas de avaliação
│   └── user.py                 # Usuários e permissões
│
├── views/                      # Rotas e controladores (MVC)
│   ├── admin.py                # Rotas administrativas
│   ├── api.py                  # Endpoints da API REST
│   ├── auth.py                 # Autenticação e autorização
│   ├── index.py                # Rotas principais
│   └── pages.py                # Páginas estáticas e dinâmicas
│
├── external/                   # Scripts externos
│   └── tasks.py                # Integração com sistema de tarefas
│
├── static/                     # Arquivos estáticos
│   ├── css/                    # Estilos CSS
│   │   ├── about.css
│   │   ├── admin.css
│   │   ├── dashboard.css
│   │   ├── documentation.css
│   │   ├── evaluation.css
│   │   ├── guidelines.css
│   │   ├── index.css
│   │   ├── modal.css
│   │   ├── nav.css
│   │   └── sign_in.css
│   │
│   ├── js/                     # Scripts JavaScript
│   │   ├── about.js
│   │   ├── admin.js
│   │   ├── dashboard.js
│   │   ├── eval.js
│   │   ├── guidelines.js
│   │   ├── heatmaps.js
│   │   ├── nav.js
│   │   └── sign_up.js
│   │
│   ├── images/                 # Imagens e ícones
│   │   └── [diversos arquivos de imagem]
│   │
│   └── dashboard/              # Dashboard React compilado
│       └── [arquivos do build]
│
├── templates/                  # Templates Jinja2 (HTML)
│   ├── base.html               # Template base
│   ├── index.html              # Página inicial
│   ├── sign_in.html            # Login
│   ├── sign_up.html            # Cadastro
│   ├── dashboard.html          # Dashboard principal
│   ├── dashboardv2.html        # Dashboard v2
│   ├── evaluations.html        # Lista de avaliações
│   ├── create_evaluation.html  # Criar avaliação
│   ├── guidelines.html         # Guidelines
│   ├── heatmaps.html           # Visualização de heatmaps
│   ├── about.html              # Sobre o projeto
│   ├── doc.html                # Documentação
│   ├── forgot_password.html    # Recuperar senha
│   ├── reset_password.html     # Resetar senha
│   └── [outros templates administrativos]
│
└── migrations/                 # Migrações de banco (Alembic)
    ├── alembic.ini            # Configuração Alembic
    ├── env.py                 # Ambiente de migração
    └── versions/              # Versões do esquema
```

## 🔧 Instalação e Configuração

### Pré-requisitos

- Python 3.10 ou superior
- Docker e Docker Compose (para banco local)
- Git

### Passo a Passo

#### 1. Clone o repositório

```bash
git clone https://github.com/alexandr10cl/SECO-Transparency-Framework.git
cd SECO-Transparency-Framework
```

#### 2. Suba o banco de dados local

```bash
docker-compose up -d
```

Isso cria um MySQL 8 local na porta 3306, com o banco `tool_portal` pronto.

#### 3. Crie um ambiente virtual Python

```bash
cd tet-website

# Windows
python -m venv venv
venv\Scripts\activate

# Linux/MacOS
python3 -m venv venv
source venv/bin/activate
```

#### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

#### 5. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

O `.env.example` já vem com as credenciais do banco Docker local. Para email e outras configs, edite o `.env` conforme necessário.

#### 6. Crie as tabelas e popule os dados de referência

```bash
# Windows
set FLASK_APP=index.py

# Linux/Mac
export FLASK_APP=index.py

# Cria as tabelas no banco
flask db upgrade

# Popula guidelines, processos, dimensões, etc.
flask seed
```

#### 7. Execute o servidor Flask

```bash
python index.py

# Ou usando Flask CLI
flask run --debug
```

O servidor estará disponível em `http://localhost:5000`

## 📱 Integração com a Extensão Chrome

Para utilizar a extensão Chrome com o sistema:

1. Acesse `chrome://extensions/` no Chrome
2. Ative o "Modo do desenvolvedor"
3. Clique em "Carregar sem compactação"
4. Selecione a pasta `tet-extension` do projeto
5. A extensão será instalada e estará pronta para uso

## 🔐 Segurança

### Práticas Implementadas

- **Senhas Criptografadas**: Uso de bcrypt para hash de senhas
- **Variáveis de Ambiente**: Credenciais sensíveis em arquivo `.env`
- **Verificação de Email**: Confirmação de cadastro via email
- **Sessões Seguras**: Gerenciamento de sessões Flask
- **CORS Configurado**: Controle de origens permitidas
- **SQL Injection Prevention**: Uso de ORM (SQLAlchemy)

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request


## 👥 Equipe

Desenvolvido pelo **LabESC** (Laboratório de Engenharia de Sistemas Complexos) da UNIRIO.

### Contato

- **Email**: 

## 🙏 Agradecimentos

- UNIRIO - Universidade Federal do Estado do Rio de Janeiro
- CAPES - Coordenação de Aperfeiçoamento de Pessoal de Nível Superior
- CNPq - Conselho Nacional de Desenvolvimento Científico e Tecnológico
- Todos os pesquisadores e desenvolvedores que contribuíram para o projeto