"""LLM -> Findings -> validacao -> LLM -> Actions.

Duas chamadas ao modelo, separadas de proposito: a segunda recebe
TODOS os findings de uma vez para poder agrupar problemas que uma unica intervencao
resolve (`F-01 + F-03 -> A-01`).

A conversa com a API nao mora aqui — e `services/ai/provider.call_ai`. Este modulo cuida
dos contratos de saida, dos prompts e da validacao tecnica, que é feita em
codigo e nao no prompt.

Os rotulos F-01 / A-01 vivem so aqui dentro, para a segunda chamada poder referenciar os
findings da primeira. Depois da validacao eles viram FKs no banco.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field


class Finding(BaseModel):
    title: str = Field(description="O problema identificado, em uma frase. Nao e uma metrica.")
    observation: str = Field(description="Sintese do que os dados mostram e por que sustentam o problema.")
    ksc_id: int = Field(description="ID de um KSC existente na lista fornecida.")
    supporting_data_ids: List[str] = Field(description="IDs de evidencia do catalogo, ex: PT-608, NAV-431, DBT-12.")


class FindingsResponse(BaseModel):
    findings: List[Finding] = Field(description="Pode ser uma lista vazia se nao houver evidencia suficiente.")


class Action(BaseModel):
    title: str = Field(description="Recomendacao concreta, resumida.")
    description: str = Field(description="O que deve ser alterado e por que isso trata os findings.")
    where: List[str] = Field(description="Onde agir: paginas, secoes ou componentes do portal.")
    finding_ids: List[str] = Field(description="Findings que esta acao resolve, ex: F-01, F-03.")


class ActionsResponse(BaseModel):
    actions: List[Action]


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_FINDINGS = """\
Você é a camada analítica do SECO-TransP, uma ferramenta de avaliação de transparência
de portais de ecossistemas de software. Você recebe os dados capturados durante uma
avaliação com desenvolvedores reais e o subconjunto do framework de transparência
(Diretrizes de transparência e seus Critérios de Sucesso (KSC, do inglês key success
criteria)) selecionado pelo gestor do portal que conduz a avaliação.

TRANSPARÊNCIA é a condição em que as informações sobre capacidades, prioridades e
comportamentos estão abertamente disponíveis, permitindo a tomada de decisão informada
pelos envolvidos e reduzindo as ineficiências causadas pela assimetria de informação.
Uma Diretriz de transparência é uma prática recomendada para aumentar a visibilidade, a
clareza e a equidade em uma área específica do portal, e um Critério de Sucesso (KSC) é o
indicador concreto usado para avaliar se essa diretriz foi efetivamente cumprida sob o
ponto de vista do desenvolvedor.

Sua única pergunta nesta etapa é: **O QUE ESTÁ ERRADO?**

REGRAS OBRIGATÓRIAS

1. EVIDENCE-FIRST. Todo finding precisa ser sustentado por dados que estão no contexto.
   Em `supporting_data_ids` use EXCLUSIVAMENTE os IDs que aparecem entre colchetes nos
   dados (formato PT-<n>, NAV-<n>, ANS-<n>, DQ-<n>, DBT-<n>). NUNCA invente um ID. NUNCA
   cite um ID que você não viu no contexto. Um ID inventado invalida o finding inteiro.

2. FRAMEWORK-ANCHORED. `ksc_id` tem que ser um dos ksc_id listados na seção do framework.
   Você NÃO cria KSCs novos e NÃO usa ksc_id fora daquela lista. Escolha o KSC que melhor
   representa o problema. Se nenhum KSC da lista se relaciona razoavelmente ao problema
   que você viu, NÃO produza o finding.

3. FINDING É PROBLEMA, NÃO MÉTRICA. Exemplos:
   - "Participante levou 120 segundos" -> ERRADO, isso é dado bruto.
   - "O participante teve dificuldade" -> ERRADO, observação genérica demais.
   - "Canais oficiais de contato apresentam baixa visibilidade" -> CERTO.
   O título deve descrever a falha de transparência do portal, não o comportamento de
   uma pessoa.

4. STATUS NÃO É FILTRO. `status=SOLVED` significa apenas que a tarefa foi concluída. NÃO
   significa que não houve problema. Um participante pode concluir a tarefa depois de
   navegação excessiva, tempo alto e deixando um comentário negativo — isso sustenta um
   finding. `NOT_SURE` é evidência de incerteza e `COULDNT_SOLVE` de dificuldade mais
   forte, mas nenhum status sozinho determina um finding. Analise TODAS as execuções.

5. OBSERVATION. Sintetize o que os dados mostram e por que eles sustentam o problema.
   Cite o tipo de sinal (comentário, navegação, tempo, nota do KSC), não repita o título.
   SEJA EXATO SOBRE QUANTAS PESSOAS. Se toda a evidência vem de um único participante,
   escreva no singular e diga de quem é: "o participante P3 levou..." — NUNCA
   "participantes enfrentaram...". Plural só quando há evidência de dois ou mais
   participantes distintos. O sistema calcula a abrangência real por fora e ela vai
   aparecer ao lado do seu texto; plural indevido deixa o card autocontraditório. O foco
   da observação é descrever o seu ACHADO (Finding), descrever o fenômeno observado.

6. VOCÊ PODE RETORNAR ZERO FINDINGS. Se os dados não sustentarem nenhum problema real,
   devolva uma lista vazia. Isso é um resultado válido e preferível a inventar problemas
   a partir de sinais fracos.

7. NÃO É SUA RESPONSABILIDADE: calcular prioridade, impacto, recorrência ou confiança;
   sugerir soluções; afirmar fatos que não estão nos dados; apontar causa raiz.

8. Combine sinais de participantes diferentes quando eles apontarem para o mesmo problema.
   Um finding sustentado por 3 participantes vale mais que 3 findings separados.

9. DIVERGÊNCIA ENTRE PARTICIPANTES É PADRÃO, NÃO RUÍDO. Quando um mesmo KSC recebe
   avaliações muito diferentes entre os participantes — parte deles satisfeita e parte
   deles reprovando o mesmo critério — isso é um sinal a investigar, não uma média a
   ignorar. Um KSC com média aceitável pode esconder um subgrupo que não conseguiu
   encontrar a informação. Olhe a distribuição das notas por participante, não só o nível
   geral, e cruze com o perfil de quem divergiu (anos de experiência, familiaridade com
   portais, segmento) para descrever a quem o problema afeta. Continue valendo a regra 5:
   descreva a abrangência com exatidão, sem transformar um subgrupo em "os participantes".

10. Escreva `title` e `observation` na linguagem dos participantes. Mantenha os títulos de KSC e
    Guideline em inglês quando precisar citá-los, como estão no banco SEMPRE.

11. NAVEGAÇÃO. Cada linha é uma página carregada no navegador do participante durante a
    tarefa, na ordem em que aconteceu; `(aba)` marca o retorno a uma aba já aberta, e não um
    novo carregamento. A captura é do navegador inteiro, não apenas do portal avaliado, então
    a trilha inclui buscadores, repositórios, fóruns, tradutores e páginas sem relação com a
    avaliação. Quando o participante usou uma busca, os termos que ele digitou aparecem na
    própria URL. Leia o percurso contra o objetivo da tarefa em que ele aconteceu e
    interprete-o como as demais evidências — nem toda trilha indica um problema.

12. DÚVIDAS. As linhas [DBT-n] são perguntas que o participante escreveu com as próprias
    palavras enquanto executava o cenário, e não depois dele: o tempo entre parênteses diz
    em que ponto do cenário a dúvida surgiu, então ela pode ser cruzada com a navegação
    daquele mesmo intervalo. É o registro mais direto de uma lacuna de informação, porque
    nomeia aquilo que o participante procurava e não encontrou — mas é o relato de uma
    dificuldade momentânea, não um defeito já confirmado do portal: uma dúvida pode ter
    sido resolvida logo em seguida pela própria navegação. Leia-a contra o objetivo da
    tarefa e contra o que aconteceu depois dela, como faz com as demais evidências.
"""
SYSTEM_ACTIONS = """\
Você é a camada analítica do SECO-TransP. Na etapa anterior foram identificados os
problemas de transparência (Findings) de uma avaliação, já validados contra os dados e
ancorados no framework (Diretrizes e seus Critérios de Sucesso (KSC)).

TRANSPARÊNCIA é a condição em que as informações sobre capacidades, prioridades e
comportamentos estão abertamente disponíveis, permitindo a tomada de decisão informada
pelos envolvidos e reduzindo as ineficiências causadas pela assimetria de informação.
Cada ação que você propõe existe para aproximar o portal dessa condição.

Sua única pergunta agora é: **O QUE DEVEMOS FAZER?**

REGRAS OBRIGATÓRIAS

1. AGRUPE. Não produza mecanicamente uma ação por finding. Se dois ou mais findings
   podem ser resolvidos pela mesma intervenção, produza UMA ação que liste todos eles em
   `finding_ids`. Exemplo: "canais de contato pouco visíveis" + "ausência de formulário
   para issues" -> uma única ação "criar widget de suporte com link para o issue tracker".

2. NADA DE AÇÃO GENÉRICA. "Melhorar a documentação" é inútil. A ação precisa responder
   O QUE muda e ONDE. `where` deve conter locais concretos do portal (páginas, seções,
   componentes, navbar, footer) inferidos das URLs e da navegação que aparecem nos
   findings. Se não der para inferir um local específico, descreva a área do portal — mas
   nunca deixe vazio.

3. COBERTURA. Todo finding recebido deve aparecer em pelo menos uma ação. Use apenas os
   IDs de finding que foram fornecidos (formato F-01, F-02, ...).

4. NÃO ESTIME PRIORIDADE, IMPACTO NEM ESFORÇO, e não mencione esses valores no texto. O
   sistema calcula a prioridade a partir das evidências que sustentam cada finding. Sua
   parte é dizer o que fazer e onde.

5. `description` deve explicar e detalhar a ação e, quando ajudar, por que ela trata aqueles
   findings. Não existe campo separado para justificativa.

6. Escreva tudo na mesma linguagem dos findings. No caso de português, coloque Ç e acentue corretamente todas as palavras.

7. O CRITÉRIO DE SUCESSO ORIENTA A AÇÃO. Cada finding é acompanhado do critério de
   sucesso (KSC) que ele viola, com sua descrição. Essa descrição enuncia o estado que se
   espera do portal quanto àquele aspecto da transparência, e é a referência a partir da
   qual a intervenção deve ser formulada: a ação proposta descreve como o portal passaria
   da situação observada nos dados para a situação descrita no critério. Não reproduza o
   texto do critério na `description` — ele é o parâmetro, não o conteúdo da recomendação;
   traduza-o numa mudança concreta neste portal, apoiada nos locais que os findings
   indicam.
"""


def build_actions_prompt(findings: List[Dict[str, Any]], evaluation) -> str:
    """Contexto da segunda chamada: os findings validados, ja com a abrangencia calculada.

    A abrangencia vai junto de proposito — ela ajuda o modelo a decidir o que agrupar,
    mas continua sendo numero do sistema, nao estimativa dele.

    Cada finding leva tambem a descricao do KSC que ele viola. So o titulo do criterio
    ("Data Currency") nao diz o que precisa mudar no portal; a descricao enuncia o estado
    desejado e e o que permite a acao ser especifica em vez de generica.
    """
    objective = " ".join((evaluation.manager_objective or "").split())
    lines = [
        "## AVALIACAO",
        f"{evaluation.name} — portal {evaluation.seco_portal} ({evaluation.seco_portal_url})",
        f"Objetivo do gestor: {objective}",
        "",
        "## FINDINGS VALIDADOS",
        "",
    ]
    for finding in findings:
        metrics = finding["metrics"]
        lines.append(f"### {finding['id']} — {finding['title']}")
        lines.append(f"Observation: {finding['observation']}")
        lines.append(
            f"KSC violado: G{finding['ksc']['guideline_id']} / ksc_id={finding['ksc']['id']} — "
            f"{finding['ksc']['title']}"
        )
        description = " ".join((finding["ksc"].get("description") or "").split())
        if description:
            lines.append(f"Criterio de sucesso a ser atendido: {description}")
        lines.append(
            f"Abrangencia calculada pelo sistema: {metrics['affected_participants']} participantes "
            f"· recorrencia {metrics['recurrence']} · confianca da evidencia {metrics['confidence_band']}"
        )
        urls = finding.get("evidence_urls") or []
        if urls:
            lines.append("Paginas envolvidas nas evidencias: " + " · ".join(urls[:8]))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fase 4 — validacao tecnica (em codigo, nao no prompt)
# ---------------------------------------------------------------------------

def validate_findings(
    raw_findings: List[Finding],
    catalog: Dict[str, Dict[str, Any]],
    scope: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa findings aceitos dos rejeitados.

    Um finding so passa se o `ksc_id` pertencer ao escopo desta avaliacao e se sobrar ao
    menos um `supporting_data_id` que exista de verdade no catalogo. ID inventado e
    descartado; se sobrarem zero evidencias, o finding inteiro cai.

    Os rejeitados sao devolvidos junto porque ver a IA errando e o sinal de que o prompt
    precisa de ajuste — eles vao para a coluna `debug` da analise.
    """
    ksc_by_id = {k["ksc_id"]: k for k in scope}
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for raw in raw_findings:
        ksc = ksc_by_id.get(raw.ksc_id)
        if ksc is None:
            rejected.append({
                "title": raw.title,
                "observation": raw.observation,
                "ksc_id": raw.ksc_id,
                "supporting_data_ids": raw.supporting_data_ids,
                "reason": (
                    f"ksc_id={raw.ksc_id} nao pertence ao escopo desta avaliacao "
                    f"(permitidos: {sorted(ksc_by_id)})"
                ),
            })
            continue

        valid_ids, invalid_ids = [], []
        for evidence_id in raw.supporting_data_ids:
            normalized = (evidence_id or "").strip().upper()
            (valid_ids if normalized in catalog else invalid_ids).append(normalized)

        # dedup preservando ordem
        valid_ids = list(dict.fromkeys(valid_ids))

        if not valid_ids:
            rejected.append({
                "title": raw.title,
                "observation": raw.observation,
                "ksc_id": raw.ksc_id,
                "supporting_data_ids": raw.supporting_data_ids,
                "reason": (
                    "nenhum supporting_data_id existe no catalogo de evidencias "
                    f"(invalidos: {invalid_ids})"
                ),
            })
            continue

        accepted.append({
            "id": None,  # atribuido depois, em ordem
            "title": raw.title,
            "observation": raw.observation,
            "ksc": {
                "id": ksc["ksc_id"],
                "title": ksc["ksc_title"],
                # A descricao segue adiante porque e ela — nao o titulo de duas palavras —
                # que define o estado desejado do portal, e portanto o alvo da acao que a
                # etapa 2 vai propor (ver `build_actions_prompt`).
                "description": ksc["ksc_description"],
                "guideline_id": ksc["guideline_id"],
                "guideline_title": ksc["guideline_title"],
                "weight": ksc.get("weight"),
            },
            "supporting_data_ids": valid_ids,
            "invalid_ids_dropped": invalid_ids,
        })

    for index, finding in enumerate(accepted, start=1):
        finding["id"] = f"F-{index:02d}"

    return accepted, rejected


def validate_actions(
    raw_actions: List[Action],
    findings: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Descarta finding_ids inexistentes; acao que nao sobra com nenhum e rejeitada."""
    known = {f["id"] for f in findings}
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for raw in raw_actions:
        valid_ids = list(dict.fromkeys(
            fid.strip().upper() for fid in raw.finding_ids if fid.strip().upper() in known
        ))
        invalid_ids = [
            fid for fid in raw.finding_ids if fid.strip().upper() not in known
        ]
        if not valid_ids:
            rejected.append({
                "title": raw.title,
                "finding_ids": raw.finding_ids,
                "reason": "nenhum finding_id existe entre os findings validados",
            })
            continue

        accepted.append({
            "id": None,
            "title": raw.title,
            "description": raw.description,
            "where": [w for w in raw.where if w and w.strip()],
            "finding_ids": valid_ids,
            "invalid_finding_ids_dropped": invalid_ids,
        })

    for index, action in enumerate(accepted, start=1):
        action["id"] = f"A-{index:02d}"

    return accepted, rejected


def uncovered_findings(
    findings: List[Dict[str, Any]], actions: List[Dict[str, Any]]
) -> List[str]:
    """Findings que nenhuma acao resolve — sinal de que o prompt da etapa 2 precisa ajuste."""
    covered = {fid for action in actions for fid in action["finding_ids"]}
    return [f["id"] for f in findings if f["id"] not in covered]
