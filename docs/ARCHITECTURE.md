# Arquitetura — SECO-TransP

Documentação técnica do framework. Para visão geral e setup, veja o [README da raiz](../README.md) e o [README do backend](../tet-website/README.md).

## Sumário

- [Visão de componentes](#visão-de-componentes)
- [Backend (MVC)](#backend-mvc)
- [Modelo de dados (ER)](#modelo-de-dados-er)
- [Fluxos principais (diagramas de sequência)](#fluxos-principais)
- [Inventário de rotas](#inventário-de-rotas)
- [Camada de serviços](#camada-de-serviços)
- [Flags e modos de operação](#flags-e-modos-de-operação)
- [Decisões arquiteturais](#decisões-arquiteturais)

## Visão de componentes

```mermaid
flowchart TB
    subgraph Extensao["Extensão Chrome (tet-extension)"]
        POPUP["popup.js<br/>UI side panel + fluxo da avaliação"]
        BG["background.js<br/>tracking de navegação via tabs API"]
    end

    subgraph Backend["Backend Flask (tet-website)"]
        VIEWS["views/<br/>index · auth · api · admin · pages"]
        EXT["external/tasks.py<br/>endpoints da extensão"]
        SERVICES["services/<br/>heatmap · cache · prefetch · email · tokens"]
        MODELS["models/<br/>SQLAlchemy ORM"]
        FLAGS["config_flags.py<br/>DEV_MODE · UXT_INTEGRATION"]
    end

    DB[("MySQL 8<br/>tool_portal")]
    UXT["UX-Tracking API<br/>uxt.liis.com.br"]
    SMTP["Servidor SMTP"]
    BROWSER["Navegador do gestor<br/>dashboards Jinja2 + JS estático"]

    POPUP --> EXT
    BG --> POPUP
    BROWSER --> VIEWS
    VIEWS --> SERVICES
    VIEWS --> MODELS
    EXT --> MODELS
    SERVICES --> MODELS
    MODELS --> DB
    SERVICES -. "se UXT_INTEGRATION" .-> UXT
    SERVICES -. "se DEV_MODE=False" .-> SMTP
    VIEWS --> FLAGS
    SERVICES --> FLAGS
```

Pontos-chave:

- **Sem SPA**: todos os dashboards são server-rendered (Jinja2) com JavaScript estático (`static/js/`). O antigo dashboard React foi removido por ser código morto.
- **`config_flags.py`** é a fonte única das flags — nenhum módulo lê `os.getenv` diretamente para `DEV_MODE`/`UXT_INTEGRATION`.
- A extensão conversa com o backend apenas por 3 endpoints (ver [fluxo da extensão](#1-fluxo-da-extensão-execução-de-uma-avaliação)).

## Backend (MVC)

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| Entry point | `index.py` | Cria o app Flask, inicializa SQLAlchemy/Migrate, importa views e models, registra CLI (`flask seed`), error handlers globais de banco |
| Views | `views/` + `external/tasks.py` | Rotas HTTP. Sem blueprints — cada módulo importa `app` de `index.py` e registra rotas com `@app.route` |
| Serviços | `services/` | Lógica de negócio reutilizável (heatmaps, cache, prefetch, email, tokens UXT) |
| Models | `models/` | ORM SQLAlchemy; todos exportados via `models/__init__.py` |
| Config | `database.py` (URI do banco) + `config_flags.py` (flags) | Configuração lida do `.env` |
| Auth helpers | `functions.py` | `isLogged()`, `isAdmin()`, decorator `login_required` |
| CLI | `commands.py` | `flask seed` — popula dados de referência de `seed_data.json` (idempotente) |

## Modelo de dados (ER)

17 tabelas de entidade + 7 associativas (24 no total). Visão por domínio:

**Domínio de referência** (populado pelo `flask seed`): guidelines, critérios de sucesso (KSC), exemplos, perguntas, processos SECO, dimensões, fatores condicionantes e de DX, tarefas.

**Domínio de avaliação** (criado pelos usuários): usuários, avaliações, pesos de KSC por avaliação e todos os dados coletados pela extensão.

```mermaid
erDiagram
    USER ||--o{ EVALUATION : "cria (SECO_MANAGER)"
    EVALUATION ||--o{ COLLECTED_DATA : "recebe sessões"
    EVALUATION ||--o{ EVALUATION_KSC_WEIGHT : "define pesos"
    KEY_SUCCESS_CRITERION ||--o{ EVALUATION_KSC_WEIGHT : ""
    EVALUATION }o--o{ SECO_PROCESS : "avalia (evaluation_SECO_process)"

    COLLECTED_DATA ||--o{ PERFORMED_TASK : ""
    COLLECTED_DATA ||--o{ NAVIGATION : ""
    COLLECTED_DATA ||--o{ ANSWER : ""
    COLLECTED_DATA ||--|| DEVELOPER_QUESTIONNAIRE : ""

    TASK ||--o{ PERFORMED_TASK : ""
    TASK ||--o{ NAVIGATION : ""
    TASK }o--o{ SECO_PROCESS : "process_task"

    GUIDELINE ||--o{ KEY_SUCCESS_CRITERION : ""
    KEY_SUCCESS_CRITERION ||--o{ EXAMPLE : ""
    KEY_SUCCESS_CRITERION ||--o{ QUESTION : ""
    QUESTION ||--o{ ANSWER : ""

    GUIDELINE }o--o{ SECO_PROCESS : "guideline_seco_process"
    GUIDELINE }o--o{ SECO_DIMENSION : "guideline_seco_dimension"
    GUIDELINE }o--o{ CONDITIONING_FACTOR : "guideline_conditioning_factor"
    GUIDELINE }o--o{ DX_FACTOR : "guideline_dx_factor"

    USER {
        int user_id PK
        string email
        string username
        binary passw "bcrypt 60 bytes (TINYBLOB)"
        enum type "ADMIN | SECO_MANAGER | USER (polimórfico)"
        bool is_verified
        string verification_token
    }
    EVALUATION {
        bigint evaluation_id PK "código da avaliação (UXT ou local)"
        string name
        string seco_portal
        string seco_portal_url
        enum seco_type "OPEN_SOURCE | HYBRID | PROPRIETARY"
        text manager_objective
        datetime created_at
        int user_id FK
    }
    COLLECTED_DATA {
        int collected_data_id PK
        datetime start_time
        datetime end_time
        string cod "código de sync do UX-Tracking"
        int sessionId
        bigint evaluation_id FK
    }
    PERFORMED_TASK {
        int performed_task_id PK
        datetime initial_timestamp
        datetime final_timestamp
        enum status "SOLVED | COULDNT_SOLVE | NOT_SURE"
        string comments
        int collected_data_id FK
        int task_id FK
    }
    NAVIGATION {
        int navigation_id PK
        enum action "PAGE_NAVIGATION | TAB_SWITCH"
        string title
        string url
        datetime timestamp
        int task_id FK
        int collected_data_id FK
    }
    DEVELOPER_QUESTIONNAIRE {
        int developer_questionnaire_id PK
        enum academic_level
        enum previus_xp
        int emotion "satisfação 1-5"
        string comments
        enum segment "academia | industry | both"
        int experience "anos"
        int collected_data_id FK "unique (1:1)"
    }
    ANSWER {
        int answer_id PK
        int answer "escala 0-100"
        int collected_data_id FK
        int question_id FK
    }
    GUIDELINE {
        int guidelineID PK
        string title
        string description
        string notes
    }
    KEY_SUCCESS_CRITERION {
        int key_success_criterion_id PK
        string title
        string description
        int guideline_id FK
    }
    EVALUATION_KSC_WEIGHT {
        bigint id PK
        int weight "0-10, soma 10 por processo"
        int ksc_id FK
        bigint evaluation_id FK
    }
    TASK {
        int task_id PK
        string title
        string description
        string summary
    }
    SECO_PROCESS {
        int seco_process_id PK
        string description
    }
    SECO_DIMENSION {
        int seco_dimension_id PK
        string name
    }
    CONDITIONING_FACTOR {
        int conditioning_factor_transp_id PK
        string description
    }
    DX_FACTOR {
        int dx_factor_id PK
        string description
    }
    EXAMPLE {
        int example_id PK
        string description
        int key_success_criterion_id FK
    }
    QUESTION {
        int question_id PK
        string question
        int key_success_criterion_id FK
    }
```

Observações:

- `User` usa **herança polimórfica single-table**: `Admin` e `SECO_MANAGER` são subclasses discriminadas pela coluna `type`.
- A tabela `task_seco_type` (não mostrada no diagrama) associa cada `Task` aos tipos de SECO em que se aplica (`OPEN_SOURCE`/`HYBRID`/`PROPRIETARY`), com constraint de unicidade.
- `evaluation_id` é o **código distribuído aos desenvolvedores** — vem da API do UX-Tracking ou de geração local aleatória de 7 dígitos (fallback com detecção de colisão).

## Fluxos principais

### 1. Fluxo da extensão (execução de uma avaliação)

```mermaid
sequenceDiagram
    actor Dev as Desenvolvedor
    participant Ext as Extensão (popup.js)
    participant BG as background.js
    participant API as Backend Flask
    participant DB as MySQL
    participant UXT as UX-Tracking

    Dev->>Ext: insere código da avaliação
    Ext->>API: POST /auth_evaluation {código}
    API->>DB: valida código, carrega processos e tarefas
    API-->>Ext: processos + tarefas da avaliação
    Ext->>API: POST /load_tasks
    API-->>Ext: detalhes das tarefas

    opt sincronização UX-Tracking
        Ext->>UXT: /data/syncsession
        UXT-->>Ext: uxt_cod + uxt_sessionId
    end

    Dev->>Ext: questionário de perfil (formação, segmento, experiência)

    loop para cada tarefa
        Dev->>Ext: executa a tarefa no portal
        BG->>BG: registra navegação (pageNavigation, tabSwitch)
        Dev->>Ext: status (solved / couldntsolve / notSure) + comentário
    end

    Dev->>Ext: revisão por processo (perguntas dos KSC, escala 0-100)
    Dev->>Ext: questionário final (emoção 1-5 + comentários)

    Ext->>API: POST /submit_tasks {performed_tasks, answers,<br/>navigation, questionários, uxt_cod, uxt_sessionId}
    API->>DB: persiste CollectedData + filhos
    API-->>Ext: confirmação
```

### 2. Fluxo de heatmap (dashboard do gestor)

```mermaid
sequenceDiagram
    actor G as Gestor
    participant Dash as dashboard.html + hotspots_heatmaps.js
    participant API as /api/heatmap-scenarios
    participant Cache as heatmap_cache (LRU, TTL 6h)
    participant Svc as heatmap_service
    participant UXT as UX-Tracking

    Note over G,UXT: no login, heatmap_prefetch já agendou as 5 avaliações<br/>mais recentes em background (ThreadPool, 10 workers)

    G->>Dash: abre /eval_dashboard/{id}
    Dash->>API: GET /api/heatmap-scenarios/{id}

    alt UXT_INTEGRATION = False
        API-->>Dash: payload vazio + uxt_disabled true (HTTP 200)
        Dash->>Dash: exibe aviso de integração desativada
    else cache hit
        API->>Cache: get_cached_payload
        Cache-->>API: payload (metadata.cached = true)
        API-->>Dash: heatmaps agregados por URL
    else cache miss
        API->>Svc: build_scenarios_payload(id, token)
        Svc->>UXT: GET /view/heatmap/code/{id}
        UXT-->>Svc: imagens + pontos de interação
        Svc->>Svc: agrega por URL, mapeia cenários,<br/>calcula data_quality_score
        Svc-->>API: payload
        API->>Cache: set_cached_payload
        API-->>Dash: heatmaps agregados por URL
    end
```

### 3. Cadastro de conta nos dois modos

```mermaid
sequenceDiagram
    actor U as Usuário
    participant W as POST /register (auth.py)
    participant UXT as UX-Tracking
    participant DB as MySQL
    participant M as SMTP

    U->>W: email, nome, senha

    alt UXT_INTEGRATION = True
        W->>UXT: POST /auth/register
        W->>UXT: GET /auth/me (id do usuário)
        W->>UXT: POST /auth/login (token admin)
        W->>UXT: POST /auth/change-role (vira SECO Manager)
        Note over W,UXT: qualquer falha bloqueia o cadastro
    else UXT_INTEGRATION = False
        Note over W: pula tudo - conta apenas local
    end

    alt DEV_MODE = True
        W->>DB: cria User já verificado (is_verified = true)
        W-->>U: pode entrar imediatamente
    else DEV_MODE = False
        W->>DB: cria User + verification_token
        W->>M: envia link de verificação
        W-->>U: confirme o email antes de entrar
    end
```

## Inventário de rotas

81 rotas no total. Autenticação: **L** = exige login, **A** = exige admin.

### `views/index.py` — avaliações e dashboards (10)

| Rota | Método | Descrição | Auth |
|------|--------|-----------|------|
| `/` | GET | Página inicial | — |
| `/evaluations` | GET | Lista avaliações do usuário (paginação, busca, ordenação) | L |
| `/evaluations/create_evaluation` | GET | Formulário de criação (gera CSRF token de sessão) | L |
| `/evaluations/create_evaluation/add_evaluation` | POST | Cria avaliação (valida CSRF, pesos KSC somando 10 por processo) | L |
| `/evaluations/<id>` | GET | Detalhe da avaliação com dados coletados | L |
| `/evaluations/<id>/edit` · `/update` · `/delete` | GET/POST | Edição e exclusão | L |
| `/eval_dashboard/<id>` | GET | Dashboard analítico da avaliação | L |
| `/view_heatmap/<id>` | GET | Página de visualização de heatmap | L |

### `views/auth.py` — autenticação (8)

| Rota | Método | Descrição | Auth |
|------|--------|-----------|------|
| `/signin` · `/auth` | GET/POST | Login (com token UXT opcional + prefetch de heatmaps) | — |
| `/signup` · `/register` | GET/POST | Cadastro (4 chamadas UXT quando integração ativa; conta local quando não) | — |
| `/verify/<token>` | GET | Verificação de email | — |
| `/logout` | GET | Encerra sessão | L |
| `/forgot-password` · `/reset-password/<id>` | GET/POST | Reset de senha via UXT (indisponível com `UXT_INTEGRATION=False`) | — |

### `views/api.py` — APIs de dados e heatmap (13)

| Rota | Descrição | Auth |
|------|-----------|------|
| `/api/heatmap-scenarios/<id>` | Heatmaps agregados por URL, com cache | L |
| `/api/heatmap-tasks/<id>` | Heatmaps segmentados por tarefa via navegação | L |
| `/api/view_heatmap/<id>` | Dados crus de heatmap do UXT | L |
| `/api/wordcloud/<id>` · `/api/wordcloud/task/<eid>/<tid>` | Frequência de palavras dos comentários (geral / por tarefa) | — |
| `/api/satisfaction/<id>` · `/api/experience-data/<id>` · `/api/grau-academico/<id>` · `/api/portal-familiarity/<id>` | Distribuições para os gráficos do dashboard | — |
| `/api/guideline/<id>` | Guideline em JSON com relacionamentos | — |
| `/api/get_pksc?ids=1,2` | KSCs por processo selecionado (alimenta o form de criação) | — |
| `/api/cache/stats` | Métricas do cache de heatmaps | L |

### `views/admin.py` — administração (38)

CRUD completo (add / edit / update / delete, todas **L+A**) para 8 recursos de referência:

| Recurso | Prefixo |
|---------|---------|
| Guidelines | `/admin/*_guideline` (+ painel em `/admin/guidelines`) |
| Processos SECO | `/admin/*_seco_process` |
| Dimensões SECO | `/admin/*_seco_dimension` |
| Fatores condicionantes | `/admin/*_conditioning_factor` |
| Fatores de DX | `/admin/*_dx_factor` |
| Critérios de sucesso (KSC) | `/admin/*_key_success_criterion` |
| Tarefas | `/admin/*_task` |
| Perguntas · Exemplos | `/admin/*_question` · `/admin/*_example` |

### `views/pages.py` — páginas públicas e utilitários (15)

| Rota | Descrição | Auth |
|------|-----------|------|
| `/doc` · `/about` · `/guidelines` | Páginas públicas | — |
| `/downloads` · `/download-extension` · `/download-uxtracking` | Download dos ZIPs das extensões | — |
| `/seco_dashboard` · `/dashboardv2` | Dashboards alternativos | L / — |
| `/heatmap-tasks/<id>` | Página de heatmaps por tarefa | L |
| `/api/ping` · `/api/check-tables` | Health checks | — |
| `/teste` · `/test-navigation` · `/api/evaluation-data` | Páginas/endpoints de teste | — |

### `external/tasks.py` — integração com a extensão (5)

| Rota | Método | Descrição |
|------|--------|-----------|
| `/auth_evaluation` | POST | Valida o código e retorna processos + tarefas |
| `/load_tasks` | POST | Carrega detalhes das tarefas |
| `/submit_tasks` | POST | Recebe o pacote completo da avaliação (tarefas, respostas, navegação, questionários) |
| `/get_data/<evaluation_id>` | GET | Consulta dados coletados |
| `/data_collected` | GET | Página de dados coletados |

## Camada de serviços

**`heatmap_service.py`** — transforma os dados crus da API do UX-Tracking em payloads de visualização: normaliza timestamps, mapeia eventos de navegação para tarefas por intervalo de tempo (`build_navigation_task_map`), agrega heatmaps por URL (`build_scenarios_payload`) e segmenta por tarefa (`segment_heatmaps_by_tasks`). Calcula um `data_quality_score` com warnings quando faltam imagens ou navegação.

**`heatmap_cache.py`** — cache LRU em memória com TTL de 6 horas e capacidade para 50 avaliações. Evita chamadas repetidas à API do UXT (que pode levar minutos para datasets grandes). Expõe `get_cache_stats()` em `/api/cache/stats`.

**`heatmap_prefetch.py`** — pré-busca assíncrona via `ThreadPoolExecutor` (10 workers). Disparada no login e na listagem de avaliações para as 5 avaliações mais recentes, deixando o dashboard quente antes do gestor abrir. Sai silenciosamente quando não há token UXT.

**`email_service.py`** — envio SMTP de emails transacionais (verificação de conta e reset de senha). Não-bloqueante: falha de envio não impede a criação da conta.

**`uxt_token_manager.py`** — gestão de tokens da API do UX-Tracking em dois níveis: token de sessão (do login do usuário) e token de serviço compartilhado (credenciais de serviço/admin), com cache, expiração com buffer de 60s e refresh automático. Com `UXT_INTEGRATION=False`, retorna `None` imediatamente sem nenhuma chamada externa.

## Flags e modos de operação

As flags são lidas **uma única vez** em `config_flags.py` (sem imports do app — zero risco de import circular) e importadas por views e serviços:

```python
from config_flags import DEV_MODE, UXT_INTEGRATION
```

| | `UXT_INTEGRATION=True` | `UXT_INTEGRATION=False` |
|---|---|---|
| **Cadastro** | 4 chamadas à API UXT antes da conta local (falha bloqueia) | Conta local direta |
| **Login** | Obtém token UXT (tolera falha) + prefetch de heatmaps | Pula chamada e prefetch |
| **Heatmaps** | Busca real na API UXT com cache | HTTP 200 com `uxt_disabled: true`; UI mostra aviso |
| **Reset de senha** | Fluxo via UXT | Indisponível (mensagem amigável) |
| **Código de avaliação** | Gerado pela API UXT (fallback local se falhar) | Gerado localmente (7 dígitos, anticolisão) |

`DEV_MODE` controla apenas a **verificação de email**: `True` → conta nasce verificada e não exige SMTP; `False` → fluxo de verificação completo. As quatro combinações de flags são válidas.

O startup loga o estado: `Startup flags: DEV_MODE=... | UXT_INTEGRATION=...`

## Decisões arquiteturais

**Baseline Alembic única.** O histórico de migrations foi consolidado na baseline `4ef2e61f029a` (cria as 24 tabelas), validada contra um banco limpo: `flask db upgrade` + `flask db check` sem drift. Bancos criados com a cadeia antiga precisam de `flask db stamp 4ef2e61f029a` (após conferir o schema). O schema é propriedade exclusiva do Alembic — `db.create_all()` é proibido.

**Seed idempotente.** `flask seed` pode rodar em todo start do container: tabelas simples checam existência por PK antes de inserir; associativas usam `INSERT IGNORE`. Por isso o compose roda `flask db upgrade && flask seed` no comando de inicialização do backend.

**Branches `main` × `dev`.** Os históricos são **não relacionados** (sem merge-base — o repositório foi recriado em algum ponto). Todo o conteúdo da `main` (snapshot de produção, nov/2025) existe na `dev` em versão mais recente, verificado por patch-equivalência. Promover `dev` → `main` exige `git push origin dev:main --force`; nunca tente merge comum.

**Mesma `.env` para Docker e venv.** No compose, `environment: SERVER: db:3306` sobrescreve o `env_file`; como `load_dotenv()` não sobrescreve variáveis já definidas, o mesmo arquivo `.env` serve para o container (rede interna) e para o venv no host (`localhost:3307`).

**CSRF em formulário crítico.** A criação de avaliação usa token de uso único salvo na sessão (`eval_form_token`), validado e consumido no POST.

**Segurança de sessão.** Cookies `HttpOnly` + `SameSite=Lax`, sessão com timeout de 24h, senhas com bcrypt (custo padrão, hash de 60 bytes em `TINYBLOB`).
