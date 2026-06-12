# TET Extension — Extensão Chrome do SECO-TransP

Extensão **Manifest V3** (side panel) usada pelos desenvolvedores para executar avaliações de transparência: recebe as tarefas da avaliação, monitora a navegação durante a execução e coleta questionários e feedback.

> 📐 O fluxo completo (diagrama de sequência) e o modelo dos dados coletados estão em [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

## Instalação (modo desenvolvedor)

1. Abra `chrome://extensions/` no Chrome
2. Ative o **Modo do desenvolvedor** (canto superior direito)
3. Clique em **Carregar sem compactação** e selecione esta pasta (`tet-extension/`)
4. A extensão abre como **side panel** ao clicar no ícone

## Apontando para o backend local

No topo do [`popup.js`](popup.js) existe um toggle dev/produção:

```javascript
const CONFIG = {
  isDevelopment: false, // true = backend local, false = produção
  DEVELOPMENT_URL: "http://127.0.0.1:5000",
  PRODUCTION_URL: "https://seco-tranp-website.vercel.app/",
  ...
};
```

Para testar com o backend local (`docker compose up` ou venv), mude `isDevelopment` para `true` e **recarregue a extensão** em `chrome://extensions/`.

## Desativando a sincronização com o UX-Tracking

A etapa de sync com o UX-Tracking é opcional. Para pular: no `popup.js`, dentro do listener do `syncButton` (busque por `// Sincronizar código com API DO UX-TRACKING`), defina:

```javascript
let uxt_mode = false; // Opção de fazer a avaliação com UX-Tracking ou não
```

> Isso é independente da flag `UXT_INTEGRATION` do backend — aqui controla apenas a coleta de interações/emoções feita pela própria extensão.

## Fluxo de uso

1. **Login** — o desenvolvedor insere o código da avaliação (fornecido pelo gestor)
2. **Sync** — sincronização opcional com o UX-Tracking (captura de interações/emoções)
3. **Questionário de perfil** — formação acadêmica, segmento, experiência
4. **Tarefas** — executa cada tarefa no portal avaliado; a navegação (páginas visitadas e trocas de aba) é registrada pelo `background.js`; ao concluir, informa o status (resolvida / não conseguiu / não tem certeza) e comenta
5. **Revisão por processo** — responde as perguntas dos critérios de sucesso (escala 0–100)
6. **Questionário final** — satisfação (1–5) e comentários gerais
7. **Envio** — todos os dados são enviados ao backend de uma vez

## Endpoints do backend utilizados

| Endpoint | Quando | Conteúdo |
|----------|--------|----------|
| `POST /auth_evaluation` | Login | Valida o código e retorna processos + tarefas |
| `POST /load_tasks` | Após o login | Detalhes das tarefas |
| `POST /submit_tasks` | Envio final | `performed_tasks`, respostas dos KSC, `navigation`, questionários, identificadores UXT |

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `manifest.json` | Manifest V3 — permissões (`tabs`, `sidePanel`, `storage`, `scripting`), service worker |
| `popup.js` | UI do side panel, máquina de fases do fluxo (`login → sync → questionnaire → task → review → processreview → finalquestionnaire → final`), montagem e envio do payload |
| `background.js` | Service worker — escuta `tabs.onUpdated` / `tabs.onActivated` e registra eventos `pageNavigation` / `tabSwitch` com URL, título, timestamp e tarefa atual |
| `popup.html` / `popup.css` | Estrutura e estilo do side panel |
