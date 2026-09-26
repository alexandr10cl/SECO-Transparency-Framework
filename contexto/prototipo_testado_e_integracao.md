# Protótipo testado e integração na ferramenta SECO-TransP

Este arquivo documenta **o que já foi implementado e testado fora da
ferramenta**, neste diretório de testes, e serve de ponto de partida para uma
sessão de Claude que vá integrar esse trabalho ao código real do SECO-TransP.
Não reabre decisões de método — essas estão fixadas em `CLAUDE.md`. Aqui o
foco é: o que existe, o que foi validado com uma chamada real, e o que falta
para virar parte da ferramenta.

---

## O que este diretório é (e o que não é)

Este é um **protótipo isolado**, fora do repositório do SECO-TransP. Ele prova
que os módulos 1–3 do pipeline funcionam de ponta a ponta contra um portal
real. Ele **não** é a ferramenta — não tem banco de dados, não tem UI de
aprovação do gestor, não tem autenticação, não persiste nada além de arquivos
JSON soltos no disco. A tarefa de integração é pegar a lógica validada aqui
(principalmente `coleta.py`, `estruturacao.py` e `personalizacao.py`) e
encaixá-la na arquitetura já existente do SECO-TransP.

## Estado de implementação por etapa do método

| Etapa do método | Módulo aqui | Status |
|---|---|---|
| 1. Entradas (descrição, link, cenário-base, diretriz) | — | Simuladas via CLI/arquivos JSON de exemplo |
| 2. Web scraping | `coleta.py` | Implementado e **testado contra portal real** |
| 3. Estruturação (sem IA) | `estruturacao.py` | Implementado e testado |
| 4. Personalização com IA (2 chamadas) | `personalizacao.py` | Implementado e **testado com chamada real à API Gemini** |
| 5. Validação automática | — | **Não implementado** |
| 6. Aprovação do gestor | — | **Não implementado** (não existe UI nem fluxo) |
| 7. Log de origem | — | **Não implementado** (nenhum dos dados de rastreabilidade é persistido; hoje só existe no JSON de saída solto em disco) |

---

## Teste real feito — o que rodou e o que saiu

Pipeline completo rodado ponta a ponta contra um portal real (não um mock):

```
python main.py https://docs.langchain.com/ -o portal.json
python testar_personalizacao.py portal.json cenario_base_exemplo.json \
    --diretriz "<diretriz de transparência de exemplo>"
```

- **Coleta (`coleta.py`)**: rodou contra `docs.langchain.com`, um site
  real com conteúdo renderizado via JS. `portal.json` resultante tem ~600
  linhas, com itens de menu, páginas coletadas (texto + links internos) e
  metadados preenchidos. Modo de coleta ficou `completo` (sem gatilho de
  degradação neste portal).
- **Estruturação (`estruturacao.py`)**: consumiu a coleta bruta e gerou o
  schema fixo sem qualquer chamada de IA — confirma que a separação física
  entre coleta/estruturação e personalização é viável na prática, não só no
  papel.
- **Personalização (`personalizacao.py`)**: as duas chamadas ao Gemini
  (`gemini-3.6-flash`, via SDK `google-genai`) rodaram com `response_schema`
  (JSON mode) contra o cenário-base de exemplo (`cenario_base_exemplo.json`,
  bloco cru `title`+`description`) e a diretriz "transparência sobre política
  de dados". **Nota:** este teste foi feito com uma versão anterior do
  módulo, em que a segmentação em etapas era feita fora da IA; o módulo foi
  desde então refatorado para que a Chamada 1 segmente e mapeie juntas (ver
  CLAUDE.md e `personalizacao.py` atuais) — o teste ainda não foi re-executado
  contra a versão nova. Resultado obtido no teste original em
  `cenario_personalizado.json`:
  - As 3 etapas do cenário-base **todas corresponderam** a algo real no
    portal (0 etapas omitidas neste teste — ainda não foi testado um caso
    com omissão real).
  - A chamada 1 apontou `campo_fonte` como caminho no JSON estruturado
    (ex.: `paginas_coletadas[6].texto`), confirmando que o modelo consegue
    seguir a restrição de só seguir campos existentes quando instruído via
    prompt + schema.
  - A chamada 2 reescreveu as etapas citando nomes reais da interface
    ("Privacy policy and disclaimers", "Support portal", "Govern"), em vez de
    linguagem genérica — validando a decisão de divergir de
    McCloskey/Farrell quanto a usar termos reais da interface.

### O que esse teste NÃO cobre ainda

- **Modo degradado** — não foi testado um portal que dispare captcha, login
  obrigatório ou falha de carregamento. A lógica existe em `coleta.py`
  (`_parece_bloqueado`, `_avaliar_modo`) mas nunca rodou contra um caso real
  de bloqueio.
- **Etapas omitidas de fato** — o único teste feito teve 100% de
  correspondência. O caminho de omissão (`etapas_omitidas` populado,
  etapa sem `campo_fonte`) só foi exercitado no código, não observado em uma
  resposta real do modelo.
- **Alucinação da IA** — não foi feito nenhum teste adversarial (portal
  pequeno/vazio, cenário-base com etapas sem correspondência óbvia) para ver
  se a chamada 1 tenta inventar `campo_fonte`. É exatamente esse risco que a
  etapa 5 (validação automática, inexistente ainda) precisa cobrir.
- **`recursos_mencionados`** (saída da estruturação) não é consumido em
  lugar nenhum da personalização hoje — os prompts em `personalizacao.py`
  passam `dados_portal` inteiro (via `json.dumps`) para a chamada 1, não um
  subconjunto filtrado. Vale reavaliar se isso é o suficiente em portais
  grandes (custo de tokens) quando for para produção.
- **Volume/custo real**: não há medição de tokens, custo ou tempo de resposta
  das chamadas ao Gemini. Relevante para RNF01 (desempenho) e para decidir se
  roda de forma síncrona ou em fila no cadastro do portal.

---

## Problemas e pontos frágeis observados no código do protótipo

Vale corrigir estes pontos ao portar para a ferramenta, não são bugs
bloqueantes no protótipo mas vão incomodar em produção:

1. **`estruturacao.py` linha ~292**: mensagem de motivo de degradação tem um
   typo (`"página inicial incessível"` — falta o "a": "inacessível") e é
   redundante com o motivo da linha anterior (`"página inicial inacessível"`).
   Os dois motivos praticamente dizem a mesma coisa por caminhos de checagem
   diferentes (`coleta.paginas[0].erro` vs. lista `uteis` vazia); ao integrar,
   vale unificar a mensagem e corrigir o texto.
2. **Chave de API em texto puro no `.env`** (`GEMINI_API_KEY`), sem
   `.env.example` no repo. Ao integrar na ferramenta real, isso precisa virar
   configuração/secret gerenciado pela infraestrutura existente do
   SECO-TransP, não um arquivo solto.
3. **`personalizacao.py` não trata resposta vazia/malformada da API** além do
   que o `response_schema` já garante estruturalmente — não há tratamento
   explícito para timeout da chamada 2 depois que a chamada 1 já rodou (custo
   perdido) nem para o caso `mapeamento.itens` vir vazio.
4. **Sem testes automatizados** (`pytest` ou similar) em nenhum dos três
   módulos — os "testes" até agora são execuções manuais via CLI contra
   API/portal reais. Antes de integrar, vale decidir a estratégia de teste
   (provavelmente: testes unitários para `estruturacao.py`, que é
   determinística e fácil de testar sem rede; testes de integração
   opcionais/marcados para `coleta.py` e `personalizacao.py`, que dependem de
   rede e de chave de API).
5. **`main.py` e `testar_personalizacao.py` são CLIs de teste**, não a
   interface real de integração — ao portar, a orquestração (rodar coleta →
   estruturação → personalização em sequência, uma vez, no cadastro do
   portal) precisa de um ponto de entrada novo dentro da ferramenta
   (job/service/task assíncrona), não um script de linha de comando.

---

## O que falta implementar para a ferramenta real

Isto é nível de esforço, não pipeline novo — o método já está fechado em
`CLAUDE.md`.

### Etapa 5 — Validação automática (RF14–RF17)
Não existe nenhum código ainda. Precisa:
- Checagem estrutural: para cada item em `justificativas`, resolver o
  caminho em `fonte` (ex. `"paginas_coletadas[6].texto"`) dentro do JSON
  estruturado (saída real da etapa 2, guardada como fonte da verdade) e
  confirmar que o campo existe.
- Checagem de conteúdo: confirmar que o texto do campo referenciado
  realmente sustenta o `recurso` citado. **Resolvido nesta sessão:** por
  correspondência textual aproximada (fuzzy matching), sem chamada de IA —
  já travado em CLAUDE.md.
- Recurso não confirmado → removido do `cenario_personalizado` e registrado
  com motivo (schema de log ainda precisa incluir isso — ver etapa 7).
- **Depende de**: schema estruturado da etapa 2 estar acessível junto com o
  resultado da etapa 4 (hoje são dois arquivos JSON soltos; na ferramenta
  precisam estar associados ao mesmo portal/versão).

### Etapa 6 — Aprovação do gestor (RF18–RF21)
Não existe nenhuma UI nem fluxo de estado. Precisa:
- Tela/endpoint que mostra: cenário final, diretriz avaliada, etapas
  omitidas, recursos removidos na validação (RNF07: não pode ser JSON cru).
- Ação de aprovar/rejeitar. Rejeitar volta para a etapa 4. **Resolvido nesta
  sessão:** regenera do zero (chamadas 1 e 2 rodam de novo) — sem edição
  prévia pelo gestor. Já travado em CLAUDE.md.
- Estado de "pendente aprovação" no cadastro do portal, para não liberar o
  cenário para avaliadores antes da aprovação.

### Etapa 7 — Log de origem (RF22–RF23)
Não existe persistência nenhuma hoje (os JSONs do protótipo são artefatos de
teste manual). Precisa:
- Modelo de dados que amarre: portal, versão do cenário-base, modo de coleta,
  justificativas, etapas omitidas, recursos removidos pela validação, dados
  da aprovação (quem, quando, aprovado/rejeitado).
- Controle de acesso restrito ao gestor do portal correspondente (RF23,
  RNF03) — depende do modelo de autenticação/autorização já existente na
  ferramenta, que este protótipo não conhece.

### Integração dos módulos 1–4 existentes
- Trigger: deve rodar uma única vez, no cadastro do portal (RF21) — hoje é
  disparado manualmente via CLI. Decidir se roda síncrono (bloqueando o
  cadastro) ou assíncrono (job em fila, gestor notificado quando o cenário
  estiver pronto para aprovação). RNF01 sugere que não deve travar a UI, o
  que aponta para assíncrono, mas isso não está travado em CLAUDE.md.
- **Resolvido nesta sessão:** a segmentação do cenário-base é feita pela IA,
  dentro da Chamada 1 (`mapear_recursos`), a partir do bloco cru
  `title`+`description` (ver `cenario_base_exemplo.json` e o dataclass
  `CenarioBase` em `personalizacao.py`). Não existe segmentação manual nem
  um passo separado a decidir — isso já está travado em CLAUDE.md.
- Configuração de infraestrutura para Playwright/Chromium dentro do ambiente
  de deploy da ferramenta (hoje só testado localmente via `venv`).

---

## Referências de código do protótipo (para reaproveitar, não reescrever do zero)

| Arquivo | O que aproveitar ao portar |
|---|---|
| `coleta.py` | Lógica de fila com priorização, detecção de bloqueio (`_parece_bloqueado`), decisão de modo degradado (`_avaliar_modo`), respeito a `robots.txt` |
| `estruturacao.py` | Schema fixo de saída, lista de ruído léxico (`_RUIDO`), limites de tamanho de texto — mas corrigir o typo e a duplicação apontados acima |
| `personalizacao.py` | Prompts das duas chamadas, os JSON Schemas (`_SCHEMA_MAPEAMENTO`, `_SCHEMA_ADAPTACAO`), a separação `mapear_recursos` / `adaptar_etapas` / `montar_resultado` |
| `cenario_base_exemplo.json` | Formato real de armazenamento do cenário-base (bloco cru `title`+`description`, sem segmentação) — é isso que chega à etapa 4; a segmentação acontece dentro da Chamada 1 |
| `cenario_personalizado.json`, `portal.json` | Exemplos reais de saída para validar contra ao implementar os módulos 5–7 |

Ver também `contexto/requisitos_personalizacao_seco_transp.md` (RF/RNF
completos) e `contexto/metodo_personalizacao_cenarios_ia_1.md` e
`contexto/mapeamento_cenarios_usabilidade.md` (fundamentação da revisão
bibliográfica) para o "porquê" por trás de cada decisão de método.
