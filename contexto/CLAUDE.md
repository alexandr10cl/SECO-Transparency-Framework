# SECO-TransP — Personalização de cenários de avaliação com IA

Contexto do projeto para sessões do Claude Code. Consolida as decisões de
método já tomadas, para não serem reabertas ou contrariadas a cada sessão.

---

## O que é este projeto

TCC que atualiza a ferramenta **SECO-TransP**, usada para avaliar
**transparência em portais de ecossistemas de software**. Durante uma
avaliação, cenários guiam o participante a interagir com o portal.

**Problema:** hoje os cenários são estáticos e idênticos para todos os
portais — genéricos demais para refletir a realidade de qualquer um deles.

**Proposta:** personalizar automaticamente esses cenários com IA, ancorando-os
em dados reais coletados de cada portal.

**Questão de pesquisa (norteia a revisão bibliográfica, não o sistema):**
"Quais métodos são utilizados na literatura para a construção de cenários de
teste de usabilidade e experiência do usuário (UX) em interfaces?"

---

## Pipeline — 7 etapas

O pipeline completo roda **uma única vez, no cadastro do portal** — nunca a
cada sessão de avaliação. Isso é deliberado: evita gargalo para o avaliador.

```
Gestor (descrição)  ─┐
Portal (link)       ─┼─→ 1. Web scraping → 2. Estruturação ─┐
Cenário-base        ─┤                                       ├─→ 3. Personalização com IA
  + diretriz        ─┘                                       ┘         │
                                                                       ▼
                          Cenário personalizado ← 5. Aprovação ← 4. Validação automática
                                                    do gestor          │
                                                       └────→ Log de origem
```

### 1. Entradas
- **Descrição textual livre** do portal, fornecida pelo gestor (única entrada nova).
- **Link do portal** — já existe na ferramenta.
- **Cenário-base** do repositório do SECO-TransP — já existe, como bloco
  único `title` + `description` em texto corrido (ver schema abaixo). **Não
  vem pré-segmentado em etapas/sub-objetivos** — a IA recebe o texto corrido.
  Quando a segmentação for necessária, é ela quem a produz, na Chamada 1 da
  etapa 4 (não existe segmentação prévia armazenada no banco).
- **Diretriz de transparência** associada ao cenário-base (relação 1:1, já no
  banco; são 7 diretrizes propostas em trabalho anterior do grupo). Cada
  diretriz já traz, além de título/descrição, um conjunto de **critérios de
  sucesso** pré-formulados (cada um com sua própria descrição e exemplo — ver
  schema abaixo); é contra esses critérios que a personalização ancora o
  cenário.

### 2. Web scraping
- Navegador **headless** (Playwright/Chromium) — portais são frequentemente SPAs.
- Coleta: estrutura de navegação, conteúdo textual de páginas-chave, metadados.
- **Modo degradado** quando a coleta falha (login, captcha, acesso negado):
  usa apenas a descrição do gestor. Sempre registrar o modo.
- `robots.txt` respeitado por padrão — a ferramenta avalia transparência,
  ignorar a política do portal seria contraditório.

### 3. Estruturação
- **DETERMINÍSTICA, SEM IA.** Regra inegociável do método.
- Organiza os dados brutos no schema fixo abaixo, sem interpretar conteúdo.
- É a "fonte da verdade" contra a qual a validação (etapa 5) confere a saída
  da IA. Se a IA entrasse aqui, essa garantia desapareceria.

### 4. Personalização com IA
- **Prompt engineering** sobre modelo já treinado. **Não há fine-tuning.**
- **Duas chamadas encadeadas**, nunca uma só:
  - **Chamada 1 (mapeamento):** primeiro segmenta o cenário-base (texto
    corrido de `title`+`description`) em etapas/sub-objetivos, depois decide,
    para cada etapa, o que é real no portal. Só confirma o que puder apontar
    num campo exato do JSON da etapa 2. Temperatura baixa.
  - **Chamada 2 (adaptação):** recebe apenas o que a chamada 1 confirmou —
    por isso nunca tem chance de inventar recurso. Temperatura moderada.
- Reescrita **ampla**: pode reestruturar frases para soar natural, desde que o
  objetivo de cada etapa continue reconhecível.
- Etapas sem correspondência real são **omitidas por inteiro**.
- Rastreabilidade acompanha **recursos e fatos**, não trechos literais de texto
  (a reescrita ampla quebraria qualquer correspondência frase a frase).
- Ambas as chamadas usam saída estruturada garantida pela API (JSON mode).

### 5. Validação automática
- **Checagem estrutural:** o campo do JSON apontado na justificativa existe?
- **Checagem de conteúdo:** o conteúdo desse campo sustenta o recurso citado?
  Feita por **correspondência textual aproximada** (fuzzy matching /
  normalização + interseção de tokens) — **sem chamada a modelo de IA**.
  Mantém a etapa 5 inteira determinística: nenhuma IA valida a saída de
  outra IA.
- Recurso não confirmado é **removido automaticamente**, com registro do motivo.
- Não confia na justificativa da IA: ela também pode ser alucinada.

### 6. Aprovação do gestor
- **Obrigatória** antes da liberação.
- O gestor vê: cenário final, diretriz avaliada, o que foi omitido, o que foi
  removido — e aprova ou rejeita. Rejeitar devolve à etapa 4, que **regenera
  o cenário do zero** (chamadas 1 e 2 rodam de novo) — não há edição prévia
  pelo gestor antes de tentar de novo.

### 7. Log de origem
- Registra: modo de coleta, timestamp, versão do cenário-base, justificativas,
  etapas omitidas, recursos removidos, dados da aprovação.
- **Acesso restrito ao gestor** do portal correspondente.
- Na prática é o mesmo conteúdo da tela de aprovação — não precisa de
  interface separada.

---

## Schema do JSON

### Entradas: cenário-base e diretriz

Cenário-base (exemplo real: `cenario_base_exemplo.json`) — bloco único, sem
segmentação:

```json
{
  "title": "...",
  "description": "texto corrido, sem etapas/sub-objetivos"
}
```

Diretriz de transparência (exemplo real: `guideline_example.json`):

```json
{
  "id": "G1",
  "titulo": "...",
  "descricao": "...",
  "procedimento_comum_seco": "...",
  "dimensoes": ["..."],
  "fatores_condicionantes": ["..."],
  "fatores_experiencia_desenvolvedor": ["..."],
  "criterios_sucesso": [
    { "titulo": "...", "descricao": "...", "exemplo": "..." }
  ],
  "notas": "..."
}
```

### Saída da etapa 2 (estruturação)

```json
{
  "portal": { "url": "...", "dominio": "..." },
  "estrutura_navegacao": { "itens_menu": ["..."] },
  "paginas_coletadas": [
    { "url": "...", "titulo": "...", "texto": "...", "links_internos": ["..."] }
  ],
  "metadados": {
    "titulo_site": "...", "meta_description": "...",
    "lang": "...", "sitemap_encontrado": true
  },
  "recursos_mencionados": ["..."],
  "modo_coleta": "completo | degradado",
  "motivos_degradacao": ["..."],
  "timestamp_coleta": "..."
}
```

### Saída da etapa 4 (personalização)

```json
{
  "cenario_personalizado": "texto final, podendo estar reestruturado",
  "etapas_omitidas": [{ "etapa": "...", "motivo": "..." }],
  "recursos_confirmados": ["..."],
  "justificativas": [{ "recurso": "...", "fonte": "caminho.no.json" }]
}
```

---

## Prompts das chamadas de IA (etapa 4)

Fonte da verdade é `personalizacao.py` — os textos abaixo são um espelho para
consulta rápida; se editar os prompts no código, atualize aqui também.

### Chamada 1 — `mapear_recursos` (segmentação + mapeamento)

```
Você está transformando um cenário genérico de teste de usabilidade em um
cenário ancorado nos dados reais de um portal de ecossistema de software.

O cenário-base abaixo NÃO vem dividido em etapas - é um bloco único de
título e descrição corrida. Sua primeira tarefa é segmentá-lo em
etapas/sub-objetivos numeradas (campo "ordem", começando em 1), preservando
a ordem lógica das ações que a descrição original propõe.

Em seguida, para CADA etapa que você criar, decida se existe correspondência
real no portal. Você só pode marcar "corresponde": true se conseguir apontar
um campo EXATO do JSON estruturado abaixo que sustente essa correspondência
(em "campo_fonte", como um caminho, ex.: "paginas_coletadas[2].texto" ou
"estrutura_navegacao.itens_menu[0]"). Se não houver correspondência clara,
marque "corresponde": false e explique o motivo em "motivo" - NÃO invente
recursos que não estão no JSON.

Diretriz de transparência associada a este cenário (inclui os critérios de
sucesso que as etapas segmentadas devem poder refletir):
{diretriz}

Cenário-base a segmentar e mapear:
Título: {titulo_cenario}
Descrição: {descricao_cenario}

Descrição do portal fornecida pelo gestor:
{descricao_gestor}

Dados reais coletados do portal (JSON estruturado, fonte da verdade):
{dados_portal}
```

`{diretriz}` e `{dados_portal}` são o JSON completo (schemas acima) serializado.
Saída: lista de itens `{ordem, objetivo, texto, corresponde, campo_fonte,
recurso_real, motivo}` — segmentação e mapeamento na mesma estrutura.

### Chamada 2 — `adaptar_etapas` (reescrita)

```
Reescreva as etapas de um cenário de teste de usabilidade para que usem os
termos reais da interface do portal avaliado, em vez de linguagem genérica.
Você só recebeu etapas já confirmadas como reais - pode e deve citar o
recurso real pelo nome, mas NÃO invente nada além do que foi informado.

A reescrita pode reestruturar frases livremente para soar natural, desde
que o objetivo de cada etapa continue reconhecível.

Diretriz de transparência associada a este cenário:
{diretriz}

Etapas confirmadas (objetivo original + recurso real encontrado no portal):
{etapas}
```

Recebe só os itens com `corresponde: true` da chamada 1 — nunca vê os
omitidos, por isso não tem como inventar recurso.

---

## Decisões travadas — não reabrir sem discussão

| Decisão | Por quê |
|---|---|
| Estruturação sem IA | Preserva a fonte da verdade para a validação |
| Segmentação do cenário-base é feita pela IA, na Chamada 1 | O cenário-base é armazenado como `title`+`description` corridos, sem segmentação prévia no banco — não há onde mais fazer isso antes da IA |
| Checagem de conteúdo (etapa 5) por correspondência textual aproximada, não por IA | Mantém o módulo de validação inteiro determinístico — nenhuma IA fica responsável por checar alucinação de outra IA |
| Rejeição do gestor (etapa 6) regenera o cenário do zero, sem edição prévia | Simplicidade de implementação; evita UI de edição e reprocessamento parcial |
| Duas chamadas de IA, não uma | Isola a decisão factual da reescrita criativa |
| Reescrita ampla, não substituição literal | Cenário precisa soar natural |
| Rastrear recursos, não trechos de texto | Robusto a qualquer nível de reescrita |
| Omitir etapa sem correspondência | Melhor que manter genérico e vago |
| Aprovação obrigatória, uma vez no cadastro | Rigor sem virar gargalo de uso |
| **Usar termos reais da interface no cenário** | Diverge de McCloskey/Farrell **de propósito** — aquela regra existe para não contaminar medição de navegação, que o SECO-TransP não mede |
| Log restrito ao gestor | Decisão de escopo |
| Sem fine-tuning | Escopo de TCC |

---

## Revisão bibliográfica — 6 estudos

| # | Referência | O que se aproveitou |
|---|---|---|
| 1 | Ekşioğlu et al. (2011) | Vincular cada cenário a um critério explícito; validar antes de aplicar |
| 2 | Ekşioğlu et al. (2013) | *Contraponto:* cenário fixo viabiliza comparação entre portais |
| 3 | Moor et al. (2022) | Dados reais como insumo; cenário em estágios sequenciais |
| 4 | Rosson & Carroll (2002) | *Claims* → log de origem; *roughness* → limite da reescrita; *root concept* → descrição do gestor |
| 5 | McCloskey (2014) | Critérios de redação (realista, acionável, sem pistas) — divergimos do último |
| 6 | Farrell (2017) | Decidir o que observar antes de escrever → duas chamadas encadeadas |

**Contribuições originais** (sem precedente na revisão, porque nenhum estudo
envolve geração por IA): estruturação determinística e validação automática
contra alucinação.

---

## Requisitos funcionais (RF01–RF23)

- **RF01** — entrada: descrição textual do portal pelo gestor
- **RF02–RF07** — coleta: navegação, conteúdo, metadados, SPA, modo degradado, registro do modo
- **RF08** — estruturação em JSON de schema fixo, sem IA
- **RF09–RF13** — personalização: segmentar, mapear, gerar, omitir, justificar
- **RF14–RF17** — validação: checagem estrutural, de conteúdo, remoção, registro
- **RF18–RF21** — aprovação: apresentar, aprovar/rejeitar, retornar, executar uma vez
- **RF22–RF23** — log de origem e restrição de acesso

Cadastro de portal por link, seleção de cenário-base e repositório de cenários
**já existem** na ferramenta — fora do escopo.

Detalhamento completo em `contexto/requisitos_personalizacao_seco_transp.md`.

---

## Requisitos não funcionais (RNF01–RNF07)

Detalhados em `contexto/requisitos_personalizacao_seco_transp.md`. Resumo:

- **RNF01 (desempenho)** — personalização não pode rodar durante a sessão do
  avaliador; decorre de RF21 (execução única, no cadastro). Aponta para
  execução assíncrona (job/fila), não síncrona bloqueando a UI.
- **RNF02 (confiabilidade)** — saídas de IA sempre em JSON validado por
  schema (já implementado em `personalizacao.py` via `response_schema`).
- **RNF03 (segurança/privacidade)** — log de origem só para o gestor do
  portal correspondente (mesma regra da etapa 7).
- **RNF04 (robustez)** — degradar graciosamente em falha de coleta (modo
  degradado), sem impedir a geração de um cenário.
- **RNF05 (auditabilidade)** — toda decisão automática (mapeamento, omissão,
  remoção) deve ser reconstruível depois — é o que o log de origem cobre.
- **RNF06 (manutenibilidade)** — a separação física entre módulo
  determinístico (estruturação) e módulos com IA deve sobreviver à
  integração — já listado em "Convenções" abaixo.
- **RNF07 (usabilidade para o gestor)** — a tela de aprovação apresenta o
  que mudou/foi omitido/foi removido de forma compreensível, **nunca como
  JSON cru**.

---

## Limitações assumidas

- **Revalidação:** o cenário reflete o portal no momento da coleta; mudanças
  posteriores não são detectadas. Documentado como trabalho futuro.
- **Comparabilidade:** personalizar por portal abre mão da comparação
  estatística entre ecossistemas que um cenário fixo permitiria.
- **Fidelidade à diretriz:** julgamento semântico, fica com o gestor, não com
  a validação automática.
- **Profundidade de rastreamento:** parâmetro em aberto; candidato a variável
  experimental (cobertura × tempo de execução).

---

## Estado do código

Implementado:
- `coleta.py` — módulo 1, scraping com Playwright
- `estruturacao.py` — módulo 2, determinístico
- `personalizacao.py` — módulo 3, duas chamadas de IA (Gemini)
- `main.py` — CLI dos módulos 1 e 2 em sequência (ainda não chama o módulo 3)

A fazer: integrar módulo 3 ao `main.py`; módulos 4 (validação) e 5
(aprovação/log); integração com o SECO-TransP existente.

Estado de teste real, problemas conhecidos do protótipo e checklist de
integração: `contexto/prototipo_testado_e_integracao.md` — leitura
obrigatória antes de começar a portar código para a ferramenta.

---

## Convenções

- Código, comentários e documentação em **português**.
- Manter a separação física entre módulos determinísticos e módulos com IA —
  é parte do método, não só organização de código.
- Toda decisão automática precisa ser registrável no log de origem.
- Ao mexer em algo listado em "decisões travadas", avisar antes em vez de
  simplesmente alterar.
