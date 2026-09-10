// Camada analitica de IA: abas Findings e Action Plan do dashboard.
//
// Fluxo: ao abrir a pagina, pergunta o estado. Se nunca foi gerada, dispara a geracao e
// entra em polling. Durante uma regeneracao os cards antigos continuam na tela com um
// aviso, em vez de a aba piscar vazia.
//
// Findings usa master-detail (lista clicavel + painel), no mesmo padrao de interacao da
// aba "Evaluated Scenarios". A troca entre findings e so um re-render local a partir de
// `lastData` — nao refaz a requisicao.
//
// Segue as convencoes dos scripts vizinhos: sem bundler, escopo isolado por IIFE,
// cadeias .then() e o id da avaliacao lido do elemento escondido #id-avaliacao.

(function () {
    var idEl = document.getElementById('id-avaliacao');
    var findingListEl = document.getElementById('findingList');
    var findingDetailEl = document.getElementById('findingDetail');
    var actionQueueEl = document.getElementById('actionsRoot');
    var planPanelEl = document.getElementById('planPanel');
    if (!idEl || !findingListEl || !findingDetailEl || !actionQueueEl || !planPanelEl) {
        return; // AI_ANALYSIS=False
    }

    var evaluationId = idEl.textContent.trim();
    var POLL_MS = 3000;
    var pollTimer = null;
    var selectedModel = null;
    var activeFindingCode = null;
    var lastData = null;

    // A imagem do mapa de calor vem DO CLIENTE, nao do servidor: exibi-la a partir do
    // backend exigiria ler o cache de 6h (que pode ter expirado) ou re-buscar da UXT no
    // GET, somando ate 150s ao dashboard. A aba Hotspots ja baixou tudo no
    // DOMContentLoaded — ver `window.SecoHeatmaps` em hotspots_heatmaps.js. Os NUMEROS,
    // esses, vem da evidencia gravada e nao dependem disto.
    var heatmapsReady = false;   // a promise ja resolveu?
    var heatmapsApi = null;      // {byUrl, metadata} ou null (fetch falhou / UXT off)

    (window.SecoHeatmaps && window.SecoHeatmaps.ready
        ? window.SecoHeatmaps.ready
        : Promise.resolve(null)
    ).then(function (api) {
        heatmapsReady = true;
        heatmapsApi = api;
        // As linhas ja renderizadas trocam o placeholder pela miniatura.
        if (lastData) renderFindings(lastData);
    });

    // Tipos de sinal AGREGADO — espelha metrics.AGGREGATE_TYPES. Dirige o rotulo "context
    // only" do grupo, o filtro de "Sources" e a contagem do cabecalho de evidencias.
    var AGGREGATE_TYPES = ['heatmap'];

    function isAggregate(type) {
        return AGGREGATE_TYPES.indexOf(type) !== -1;
    }

    // Icone e cor por tipo de evidencia. No heatmap o icone so aparece no placeholder:
    // quando ha imagem, a miniatura ocupa o lugar dele.
    var EVIDENCE_TYPE = {
        performed_task: { icon: 'task_alt', cls: 'ev-task' },
        navigation: { icon: 'explore', cls: 'ev-nav' },
        answer: { icon: 'bar_chart', cls: 'ev-answer' },
        developer_questionnaire: { icon: 'person', cls: 'ev-profile' },
        doubt: { icon: 'help', cls: 'ev-doubt' },
        heatmap: { icon: 'blur_on', cls: 'ev-heatmap' }
    };

    // Ordem e rotulo dos grupos de evidencia no painel de detalhe. `navigation` nao tem
    // grupo proprio: ela embutida dentro de "Experience during scenarios" junto de
    // performed_task, porque e um sinal de baixo valor sozinha para o gestor mas ainda
    // vale mostrar como linha extra dentro do contexto do cenario. Grupo sem nenhuma
    // evidencia e omitido.
    // ATENCAO: um tipo que nao esteja em nenhum grupo aqui NAO e renderizado — o filtro
    // abaixo (evidenceGroupsHTML) o descarta em silencio, enquanto o contador do cabecalho
    // continua contando o array inteiro. Tipo novo no catalogo exige entrada nesta lista.
    var EVIDENCE_GROUPS = [
        { types: ['performed_task', 'navigation'], label: 'Experience during scenarios' },
        { types: ['doubt'], label: 'Questions raised during scenarios' },
        { types: ['answer'], label: 'Success criterion assessment' },
        { types: ['developer_questionnaire'], label: 'Participant profile & feedback' },
        // Por ultimo e marcado como contexto: o rotulo diz o que o dado E (distribuicao
        // de interacoes), nunca o que ele NAO e (atencao / olhar / percepcao).
        { types: ['heatmap'], label: 'Interaction distribution by page', contextOnly: true }
    ];

    // "impact 4/4" era lido como nota (4 de 4 = bom? ruim?). Nao e nota: e alcance — a
    // uniao dos participantes atingidos pelos findings que a acao resolve, sobre o total
    // (metrics.compute_action_metrics). A segunda frase existe so para dizer para que
    // lado o numero e melhor, que era exatamente a duvida dos usuarios.
    var IMPACT_HELP = 'Participants this action would help, out of the total. ' +
        'Higher means broader reach.';

    // ---------------------------------------------------------------- helpers

    function esc(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/[&<>"]/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
            });
    }

    function each(selector, fn) {
        Array.prototype.forEach.call(document.querySelectorAll(selector), fn);
    }

    function confidenceBadgeClass(band) {
        return 'ai-badge ai-conf-' + esc(String(band || 'low').toLowerCase());
    }

    function priorityBadgeClass(band) {
        return 'ai-badge ai-prio-' + esc(String(band || 'low').toLowerCase());
    }

    function formatDate(iso) {
        if (!iso) return '—';
        var date = new Date(iso);
        return isNaN(date.getTime()) ? iso : date.toLocaleString();
    }

    function formatTokens(total) {
        if (!total) return null;
        return total >= 1000 ? (total / 1000).toFixed(1) + 'k tokens' : total + ' tokens';
    }

    function goToTab(label) {
        var items = document.querySelectorAll('.dashboard-navbar ul li');
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim() === label) { items[i].click(); return; }
        }
    }

    // `cls` permite realcar elementos fora dos cards da IA: a linha do KSC na aba
    // Evaluated Scenarios e um <tr>, e outline em <tr> (o que .ai-highlight usa) nao
    // renderiza de forma consistente entre navegadores.
    function highlight(el, cls) {
        if (!el) return;
        var className = cls || 'ai-highlight';
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add(className);
        setTimeout(function () { el.classList.remove(className); }, 1600);
    }

    // Leva a aba Evaluated Scenarios e para na linha do KSC dentro da tabela de Key
    // Success Criteria. A ancora e o id real do criterio (data-ksc-id, renderizado em
    // dashboard.html) — o mesmo key_success_criterion_id que a IA usa em finding.ksc.id.
    function goToScenarioKsc(kscId) {
        var row = document.querySelector('.scenario-panel tr[data-ksc-id="' + kscId + '"]');
        if (!row) return;

        goToTab('Evaluated Scenarios');

        // Clicar no item da sidebar reaproveita initScenariosSidebar (dashboard.js): troca
        // o painel e ainda gera a word cloud do cenario, que duplicar aqui perderia.
        var panel = row.closest('.scenario-panel');
        if (panel && !panel.classList.contains('active')) {
            var item = document.querySelector(
                '.scenario-item[data-scenario-id="' + panel.dataset.scenarioId + '"]');
            if (item) item.click();
        }

        // A tabela vive dentro do accordion da diretriz, fechado por padrao. O handler de
        // dashboard.js e toggle, entao so clica quando esta fechado.
        var accordion = row.closest('.guideline-accordion-item');
        if (accordion && !accordion.classList.contains('active')) {
            var header = accordion.querySelector('.guideline-accordion-header');
            if (header) header.click();
        }

        highlight(row, 'ksc-row-highlight');
    }

    // O nome do portal ja esta renderizado no masthead da avaliacao — lido do DOM em vez
    // de duplicar no payload da API.
    function portalName() {
        var el = document.getElementById('evaluation-portal-name');
        return el ? el.textContent.trim() : '';
    }

    function emptyBox(message) {
        return '<div class="ai-empty">' + message + '</div>';
    }

    // Por que esta analise nao tem mapa de calor. Mesmas chaves de `REASON_LABEL`
    // (services/ai/heatmap_evidence.py), em ingles e sem jargao.
    var HEATMAP_REASON = {
        disabled: 'turned off',
        uxt_disabled: 'UX-Tracking integration off',
        no_token: 'session expired',
        ownership: 'another UX-Tracking account owns this evaluation',
        unauthorized: 'UX-Tracking rejected the session',
        timeout: 'UX-Tracking timed out',
        unreachable: 'UX-Tracking unreachable',
        no_sessions: 'no sessions collected',
        no_images: 'UX-Tracking returned no usable images',
        error: 'fetch failed'
    };

    function heatmapStatLabel(heatmap) {
        if (!heatmap) return '';
        if (heatmap.pages) {
            return heatmap.pages + ' heatmap page' + (heatmap.pages === 1 ? '' : 's');
        }
        if (!heatmap.reason) return '';
        return 'heatmaps unavailable (' +
            (HEATMAP_REASON[heatmap.reason] || heatmap.reason) + ')';
    }

    // ---------------------------------------------------------------- cabecalho

    function renderControls(data) {
        var meta = [];
        if (data.generated_at) meta.push('Generated ' + esc(formatDate(data.generated_at)));
        if (data.model) meta.push(esc(data.model));
        var tokens = formatTokens(data.stats && data.stats.tokens_total);
        if (tokens) meta.push(esc(tokens));
        if (data.stats && data.stats.ai_duration_s) meta.push(esc(Math.round(data.stats.ai_duration_s)) + 's');
        // Sem isto uma analise que enxergou mapas de calor e uma que rodou texto-so sao
        // visualmente identicas.
        var heatmapStat = heatmapStatLabel(data.stats && data.stats.heatmap);
        if (heatmapStat) meta.push(esc(heatmapStat));

        var html = meta.length ? '<div class="ai-meta">' + meta.join(' · ') + '</div>' : '';

        if (data.can_regenerate) {
            var options = (data.available_models || []).map(function (model) {
                var chosen = model === (selectedModel || data.model) ? ' selected' : '';
                return '<option value="' + esc(model) + '"' + chosen + '>' + esc(model) + '</option>';
            }).join('');
            var busy = data.status === 'RUNNING' || data.status === 'PENDING';
            html += '<div class="ai-actions">' +
                (options ? '<select class="ai-model-select" data-ai-model>' + options + '</select>' : '') +
                '<button class="ai-btn" data-ai-generate' + (busy ? ' disabled' : '') + '>' +
                (busy ? 'Generating…' : (data.status === 'NONE' ? 'Analyze' : 'Regenerate')) +
                '</button></div>';
        }

        each('[data-ai-controls]', function (el) { el.innerHTML = html; });
    }

    function renderState(data) {
        var html = '';
        var hasCards = (data.findings || []).length || (data.actions || []).length;

        if (data.status === 'RUNNING' || data.status === 'PENDING') {
            html = '<div class="ai-note ai-note-busy"><span class="ai-spinner"></span>' +
                (hasCards
                    ? 'Regenerating the analysis. The cards below are the previous result.'
                    : 'Reading the evaluation data and running the analysis. This takes a couple of minutes.') +
                '</div>';
        } else if (data.status === 'ERROR') {
            html = '<div class="ai-note ai-note-error">' +
                '<strong>The analysis failed.</strong> ' + esc(data.error || '') +
                (hasCards ? ' The cards below are the last successful result.' : '') +
                '</div>';
        } else if (data.status === 'NONE') {
            html = '<div class="ai-note">No analysis yet for this evaluation.</div>';
        }

        each('[data-ai-state]', function (el) { el.innerHTML = html; });
    }

    // ---------------------------------------------------------------- findings

    // O snapshot gravado em ai_finding.evidence (o que a API de leitura serve) so guarda
    // id/type/participant_id/task_id/summary — o payload estruturado do catalogo
    // (metrics.build_evidence_snapshot) nao persiste. Por isso a leitura humana precisa
    // ser extraida do `summary`, cujo formato e fixo por tipo (context_builder.py):
    //   performed_task: "status=SUCCESS · 247s · comentario: "texto"" | "· sem comentario"
    //   navigation:     "CLICK · "titulo" · url · 14:32:10"
    //   answer:         "KSC 17 "titulo" -> 27/100"
    //   questionnaire:  "GRADUATION · usa portais OFTEN · 4 anos de xp · segmento
    //                    BACKEND · emocao 2/5 · comentario final: "texto""
    //   doubt:          "duvida em 01:23 de cenario: "texto""
    var RE_STATUS = /^status=([A-Za-z_]+)/;
    var RE_DURATION = /·\s*(\d+)s/;
    var RE_QUOTED_COMMENT = /comentario(?:\s+final)?:\s*"([^"]*)"/;
    var RE_ANSWER_SCORE = /->\s*(\d+)\/100/;
    var RE_NAV_ACTION = /^([A-Za-z_]+)\s*·\s*"([^"]*)"/;
    var RE_DOUBT_ELAPSED = /^duvida em (\S+) de cenario/;
    var RE_DOUBT_TEXT = /de cenario:\s*"([^"]*)"/;
    var RE_PROFILE = /^([A-Za-z_]+)\s*·\s*usa portais ([A-Za-z_]+)\s*·\s*(\d+)\s*anos de xp\s*·\s*segmento ([A-Za-z_]+)\s*·\s*emocao (\d)\/5/;

    var STATUS_LABEL = {
        SUCCESS: 'Completed', FAIL: 'Failed', FAILED: 'Failed',
        ABANDONED: 'Abandoned', SKIPPED: 'Skipped'
    };

    function humanize(token) {
        return String(token || '').toLowerCase().replace(/_/g, ' ');
    }

    // Texto principal de uma linha de evidencia, extraido do `summary` cru para leitura
    // humana — "Task 5 · Completed · 247s" em vez do dump tecnico "status=SUCCESS · ...".
    function evidenceLead(item) {
        var summary = item.summary || '';
        if (item.type === 'performed_task') {
            var status = RE_STATUS.exec(summary);
            var duration = RE_DURATION.exec(summary);
            var statusLabel = status ? (STATUS_LABEL[status[1]] || humanize(status[1])) : '';
            return 'Scenario ' + esc(item.task_id) +
                (statusLabel ? ' · ' + esc(statusLabel) : '') +
                (duration ? ' · ' + esc(duration[1]) + 's' : '');
        }
        if (item.type === 'navigation') {
            var nav = RE_NAV_ACTION.exec(summary);
            return nav ? esc(nav[1]) + (nav[2] ? ' — ' + esc(nav[2]) : '') : esc(summary);
        }
        if (item.type === 'answer') {
            var score = RE_ANSWER_SCORE.exec(summary);
            return (score ? esc(score[1]) : '?') + ' / 100';
        }
        if (item.type === 'developer_questionnaire') {
            var profile = RE_PROFILE.exec(summary);
            if (!profile) return 'Profile & final feedback';
            return esc(humanize(profile[1])) + ' · ' + esc(profile[3]) + ' yrs xp · ' +
                esc(humanize(profile[4])) + ' · emotion ' + esc(profile[5]) + '/5';
        }
        if (item.type === 'doubt') {
            var elapsed = RE_DOUBT_ELAPSED.exec(summary);
            return 'Scenario ' + esc(item.task_id) +
                (elapsed && elapsed[1] !== '?' ? ' · asked at ' + esc(elapsed[1]) : '');
        }
        return esc(summary);
    }

    // Comentario/citacao entre aspas, quando existir — a parte que realmente da cor
    // humana a evidencia. Ausente para navigation e answer (sem texto livre no summary).
    function evidenceQuote(item) {
        if (item.type === 'doubt') {
            var doubt = RE_DOUBT_TEXT.exec(item.summary || '');
            return doubt && doubt[1] ? '"' + esc(doubt[1]) + '"' : '';
        }
        if (item.type !== 'performed_task' && item.type !== 'developer_questionnaire') return '';
        var match = RE_QUOTED_COMMENT.exec(item.summary || '');
        return match && match[1] ? '"' + esc(match[1]) + '"' : '';
    }

    // ------------------------------------------------- mapa de calor por pagina
    //
    // Os numeros saem de `item.payload`, gravado no snapshot da evidencia
    // (metrics.build_evidence_snapshot): URL, contagens e zonas com `x`/`y`. A imagem e a
    // unica coisa que vem do payload ao vivo da aba Hotspots — e ilustracao.
    //
    // A zona e nomeada por `SecoHeatmaps.describeZone`, a MESMA funcao da aba Hotspots:
    // `x`/`y` sao COORDENADA (onde a zona fica) e `count` e a medida. O percentual so
    // aparece no `title`, como a UX-Tracking o entrega — o denominador ela nao declara.

    function zoneLabel(hotspot) {
        return (window.SecoHeatmaps && window.SecoHeatmaps.describeZone)
            ? window.SecoHeatmaps.describeZone({
                center_x_percent: hotspot.x, center_y_percent: hotspot.y
            })
            : (hotspot.zone_id || 'zone');
    }

    // A pagina no payload AO VIVO da aba Hotspots, ou null. `byUrl` aceita a URL compacta
    // (a que a evidencia guarda) e a crua.
    function heatmapPage(url) {
        if (!heatmapsApi || !url) return null;
        return heatmapsApi.byUrl(url);
    }

    function heatmapCardFor(page) {
        if (!page || !page.url) return null;
        var cards = document.querySelectorAll('.heatmap-card');
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].dataset.url === page.url) return cards[i];
        }
        return null;
    }

    function heatmapAlt(hm) {
        var lead = 'Interaction distribution over ' + (hm.url || 'this page');
        if (!hm.hotspots.length) return lead;
        var top = hm.hotspots[0];
        return lead + ' — most interactions in the ' + zoneLabel(top) + ' zone (' +
            top.count + ' of ' + hm.interactions + ' recorded)';
    }

    function heatmapThumbHTML(hm, page) {
        if (page && page.image) {
            return '<button type="button" class="ev-thumb" data-ai-hm-expand="' + esc(hm.url) +
                '" title="Expand image">' +
                '<img src="data:' + esc(page.mime || 'image/jpeg') + ';base64,' + esc(page.image) +
                '" alt="' + esc(heatmapAlt(hm)) + '"></button>';
        }
        return '<span class="ev-thumb ev-thumb-missing" aria-hidden="true">' +
            '<span class="material-symbols-outlined">image_not_supported</span></span>';
    }

    // Nota discreta quando a captura ao vivo ja nao e a que a analise viu. Sem isto a linha
    // afirmaria "5 sessions" ao lado de uma imagem que ja e de 7.
    function heatmapDriftHTML(hm) {
        if (!heatmapsApi || !hm.sessions) return '';
        var live = Number((heatmapsApi.metadata || {}).sessions_analyzed);
        if (!live || live === hm.sessions) return '';
        var note = live > hm.sessions
            ? 'The page has new sessions since this analysis'
            : 'The session count changed since this analysis';
        return '<span class="ev-drift">' + note + ' (' + live + ' now, ' +
            hm.sessions + ' then).</span>';
    }

    function heatmapChipsHTML(hm, page) {
        // Cenarios: CONTEXTO de onde a pagina foi visitada, nunca dono do calor. Os
        // titulos so existem no payload ao vivo; sem ele, o ID ja diz qual e.
        var live = (page && page.scenarios_involved) || [];
        var chips = live.length
            ? live.map(function (scenario) {
                return '<span class="ev-scenario">' +
                    esc(scenario.scenario_title || ('Scenario ' + scenario.task_id)) + '</span>';
            }).join('')
            : hm.scenarios.map(function (id) {
                return '<span class="ev-scenario">Scenario ' + esc(id) + '</span>';
            }).join('');

        chips += hm.hotspots.map(function (hotspot) {
            return '<span class="ev-zone" title="' + esc(hotspot.percentage) +
                '% as reported by UX-Tracking">' +
                '<b>' + esc(hotspot.count) + '</b>' + esc(zoneLabel(hotspot)) + '</span>';
        }).join('');

        return chips ? '<span class="ev-chips">' + chips + '</span>' : '';
    }

    // A decisao e tomada NO RENDER, contra o card real: se a aba ainda nao carregou, esta
    // em erro, ou a UXT esta desligada, o link simplesmente nao e emitido.
    function heatmapLinkHTML(hm, page) {
        if (!heatmapCardFor(page)) return '';
        return '<span class="ev-links">' +
            '<button type="button" class="ev-hm-link" data-ai-hm-goto="' + esc(hm.url) + '">' +
            '<span class="material-symbols-outlined">north_east</span>' +
            'View in Hotspots</button></span>';
    }

    // Tres desvios deliberados da .ev-row comum: a URL ocupa o slot que nas outras linhas
    // e do participante (um sinal agregado nao pode virar, visualmente, uma pessoa de
    // identidade desconhecida — o backend mapeia participant_id ausente para "?"), a
    // miniatura substitui o icone de 28px, e o corpo cresce para quatro faixas.
    function heatmapRow(item) {
        var hm = item.payload;
        if (!hm || !hm.url) {
            // Evidencia gravada antes do payload existir: mostra o texto cru em vez de
            // sumir da tela.
            return '<div class="ev-row ev-generic">' +
                '<span class="ev-icon"><span class="material-symbols-outlined">blur_on</span></span>' +
                '<div class="ev-body"><span class="ev-lead">' + esc(item.summary || '') + '</span></div>' +
                '<span class="ev-id">' + esc(item.id) + '</span></div>';
        }
        hm = {
            url: hm.url,
            interactions: hm.interactions || 0,
            sessions: hm.sessions || 0,
            scenarios: hm.scenarios || [],
            hotspots: hm.hotspots || []
        };

        var page = heatmapPage(hm.url);
        var foot = esc(hm.interactions) + ' interactions recorded across ' +
            esc(hm.sessions) + ' session' + (hm.sessions === 1 ? '' : 's') +
            ' · <em class="ev-combined">all scenarios combined</em>';
        foot += (heatmapsReady && heatmapsApi && !page)
            ? '<span class="ev-drift">This page is no longer in the current heatmap data.</span>'
            : heatmapDriftHTML(hm);

        return '<div class="ev-row ev-heatmap">' +
            heatmapThumbHTML(hm, page) +
            '<div class="ev-body">' +
                '<span class="ev-page">' + esc(hm.url) + '</span>' +
                heatmapChipsHTML(hm, page) +
                '<span class="ev-foot">' + foot + '</span>' +
                heatmapLinkHTML(hm, page) +
            '</div>' +
            '<span class="ev-id" title="Evidence record ID, for traceability">' +
                esc(item.id) + '</span>' +
        '</div>';
    }

    // Perfil do participante como uma faixa de mini-stats, no mesmo vocabulario visual do
    // Developer Journey (.journey-profile-*, dashboard.css): icone colorido por categoria
    // + rotulo pequeno + valor. Aqui em escala reduzida, para nao competir com o resto da
    // linha de evidencia.
    var PROFILE_STAT = [
        { key: 1, icon: 'school', label: 'Education', cls: 'ev-pill-academic' },
        { key: 3, icon: 'work_history', label: 'Experience', cls: 'ev-pill-experience',
            format: function (v) { return v + ' yr' + (v === '1' ? '' : 's') + ' xp'; } },
        { key: 4, icon: 'domain', label: 'Segment', cls: 'ev-pill-segment' },
        { key: 2, icon: 'travel_explore', label: 'Portal use', cls: 'ev-pill-familiarity' },
        { key: 5, icon: 'mood', label: 'Emotion', cls: 'ev-pill-emotion',
            format: function (v) { return v + '/5'; } }
    ];

    function profileStatsHTML(item) {
        var profile = RE_PROFILE.exec(item.summary || '');
        if (!profile) return '';
        // RE_PROFILE captura, em ordem: academic_level, portal_familiarity,
        // experience_years, segment, emotion — indexes 1..5.
        return PROFILE_STAT.map(function (stat) {
            var raw = profile[stat.key];
            var value = stat.format ? stat.format(raw) : humanize(raw);
            return '<span class="ev-profile-stat ' + stat.cls + '">' +
                '<span class="material-symbols-outlined">' + stat.icon + '</span>' +
                '<b>' + esc(value) + '</b>' +
            '</span>';
        }).join('');
    }

    function evidenceRow(item) {
        if (item.type === 'heatmap') return heatmapRow(item);
        var meta = EVIDENCE_TYPE[item.type] || { icon: 'description', cls: 'ev-generic' };
        var quote = evidenceQuote(item);
        var profileStats = item.type === 'developer_questionnaire' ? profileStatsHTML(item) : '';
        return '<div class="ev-row ' + meta.cls + '">' +
            '<span class="ev-icon"><span class="material-symbols-outlined">' + meta.icon + '</span></span>' +
            '<div class="ev-body">' +
                '<span class="ev-who">' + esc(item.participant || '?') + '</span>' +
                (profileStats
                    ? '<span class="ev-profile-stats">' + profileStats + '</span>'
                    : '<span class="ev-lead">' + evidenceLead(item) + '</span>') +
                (quote ? '<p class="ev-text">' + quote + '</p>' : '') +
            '</div>' +
            '<span class="ev-id" title="Evidence record ID, for traceability">' + esc(item.id) + '</span>' +
        '</div>';
    }

    var RE_ANSWER_KSC_TITLE = /^KSC\s+\d+\s+"([^"]*)"/;

    // Um finding pode reunir respostas de mais de um KSC (raro, mas o schema permite).
    // Quando so ha um, o titulo entra no cabecalho do grupo; quando ha mais, cada
    // resposta carrega seu proprio titulo de KSC na linha.
    function answerGroupLabel(items) {
        var titles = {};
        items.forEach(function (item) {
            var match = RE_ANSWER_KSC_TITLE.exec(item.summary || '');
            if (match && match[1]) titles[match[1]] = true;
        });
        var distinct = Object.keys(titles);
        return distinct.length === 1 ? 'Success criterion assessment — ' + esc(distinct[0]) : 'Success criterion assessment';
    }

    function evidenceGroupHTML(group, items) {
        if (!items.length) return '';
        var label = group.types[0] === 'answer' ? answerGroupLabel(items) : group.label;
        return '<div class="ev-group">' +
            '<h6 class="ev-group-title">' + label + '</h6>' +
            items.map(evidenceRow).join('') +
        '</div>';
    }

    function evidenceGroupsHTML(evidence) {
        return EVIDENCE_GROUPS.map(function (group) {
            var items = evidence.filter(function (item) { return group.types.indexOf(item.type) !== -1; });
            return evidenceGroupHTML(group, items);
        }).join('');
    }

    function findingListItemHTML(finding) {
        var m = finding.metrics || {};
        var active = finding.code === activeFindingCode ? ' active' : '';
        return '<button class="ai-finding-item' + active + '" data-ai-finding-item="' + esc(finding.code) + '">' +
            '<span class="fi-code">' + esc(finding.code) + '</span>' +
            '<h4>' + esc(finding.title) + '</h4>' +
            '<div class="fi-meta">' +
                '<span>' + esc(m.affected_participants) + ' affected</span>' +
            '</div></button>';
    }

    // Atalho para o KSC na aba Evaluated Scenarios, ao lado da tag da diretriz. So e
    // emitido quando a linha existe de fato: aquela tabela lista apenas diretrizes que
    // tiveram respostas nesta avaliacao, entao um KSC sem dados nao ganha link morto.
    function kscScenarioChipHTML(ksc) {
        if (!ksc || ksc.id === null || ksc.id === undefined) return '';
        if (!document.querySelector('.scenario-panel tr[data-ksc-id="' + ksc.id + '"]')) return '';
        return '<button type="button" class="ai-anchor" data-ai-ksc-scenario="' + esc(ksc.id) + '">' +
            '<span class="material-symbols-outlined">travel_explore</span>' +
            'View in Evaluated Scenarios' +
            '<span class="material-symbols-outlined ai-anchor-expand">arrow_forward</span>' +
        '</button>';
    }

    // Caminho inverso do "resolves F-01" que ja existe no card de action.
    function actionsResolving(code) {
        return ((lastData && lastData.actions) || []).filter(function (action) {
            return (action.resolves || []).indexOf(code) !== -1;
        });
    }

    function recommendedActionsHTML(finding) {
        var actions = actionsResolving(finding.code);
        var rows = actions.map(function (action) {
            var dismissed = action.decision === 'DISMISSED' ? ' fd-action-dismissed' : '';
            return '<button type="button" class="fd-action-link' + dismissed +
                '" data-ai-action-jump="' + esc(action.code) + '">' +
                '<span class="ai-code">' + esc(action.code) + '</span>' +
                '<span class="fd-action-title">' + esc(action.title) + '</span>' +
                '<span class="' + priorityBadgeClass(action.priority_band) + '">' +
                    esc(action.priority_band) + '</span>' +
                '<span class="material-symbols-outlined fd-action-go">arrow_forward</span>' +
            '</button>';
        }).join('');

        return '<div class="fd-actions">' +
            '<h5>Recommended actions</h5>' +
            (rows || '<p class="fd-actions-empty">No action in the plan resolves this finding yet.</p>') +
        '</div>';
    }

    // Tooltip do badge de confianca. Escrito em ingles aqui (nao reusa
    // `data.formulas.confidence`, que vem em portugues do backend para o terminal/CLI).
    // Cada oracao tem sua propria linha (`\n`, preservado pelo CSS via `pre-line`) em vez
    // de uma frase corrida: deixar o navegador decidir onde quebrar produzia uma palavra
    // orfa sozinha na linha seguinte ("evidence types.", "neither.", "MEDIUM." isolados —
    // esse ultimo ainda pior por separar a seta do resultado que ela aponta). Quebrando no
    // limite de cada oracao, a seta fica colada ao rotulo de confianca que ela introduz.
    function confidenceTooltip(m) {
        var nParticipants = m.participants_affected;
        var nTypes = (m.evidence_types || []).filter(function (t) { return !isAggregate(t); }).length;
        return 'HIGH needs 2+ distinct participants\n' +
            'AND 2+ distinct evidence types.\n' +
            'MEDIUM needs only one of the two.\n' +
            'LOW needs neither.\n\n' +
            'This finding: ' + nParticipants + ' participant' + (nParticipants === 1 ? '' : 's') +
            ', ' + nTypes + ' evidence type' + (nTypes === 1 ? '' : 's') + '\n' +
            '→ ' + (m.confidence_band || '?') + '.';
    }

    function findingDetailHTML(finding) {
        if (!finding) return '';
        var m = finding.metrics || {};
        var ksc = finding.ksc || {};
        var evidence = finding.evidence || [];

        return '<div class="fd-head">' +
                '<span class="ai-code">' + esc(finding.code) + '</span>' +
                '<h2>' + esc(finding.title) + '</h2>' +
                '<span class="' + confidenceBadgeClass(m.confidence_band) + ' ai-stat-help"' +
                    ' tabindex="0" data-help="' + esc(confidenceTooltip(m)) + '">CONFIDENCE: ' +
                    esc(m.confidence_band) + '</span>' +
            '</div>' +
            '<div class="ai-stats">' +
                '<span><strong>' + esc(m.affected_participants) + '</strong> participants affected</span>' +
            '</div>' +
            '<p class="ai-observation">' + esc(finding.observation) + '</p>' +
            '<div class="fd-anchors">' +
            '<button type="button" class="ai-anchor" data-ai-ksc-anchor' +
                ' data-ksc-guideline="' + esc(ksc.guideline_id) + '"' +
                ' data-ksc-guideline-title="' + esc(ksc.guideline_title) + '"' +
                ' data-ksc-id="' + esc(ksc.id) + '"' +
                ' data-ksc-title="' + esc(ksc.title) + '"' +
                ' data-ksc-description="' + esc(ksc.description) + '">' +
                '<span class="material-symbols-outlined">menu_book</span>' +
                'G' + esc(ksc.guideline_id) + ' · KSC ' + esc(ksc.id) + ' — ' + esc(ksc.title) +
                '<span class="material-symbols-outlined ai-anchor-expand">open_in_new</span>' +
            '</button>' +
            kscScenarioChipHTML(ksc) +
            '</div>' +
            '<div class="fd-evidence">' +
                '<div class="fd-evidence-head">' +
                    '<h5>Evidence supporting this finding</h5>' +
                '</div>' +
                evidenceGroupsHTML(evidence) +
            '</div>' +
            recommendedActionsHTML(finding);
    }

    function renderFindings(data) {
        var findings = data.findings || [];
        var busy = data.status === 'RUNNING' || data.status === 'PENDING';

        if (!findings.length) {
            findingListEl.innerHTML = '';
            findingDetailEl.innerHTML = busy ? '' : emptyBox(
                'No findings for this evaluation. That is a valid result: the analysis ' +
                'returns nothing rather than inventing problems from weak signals.');
            return;
        }

        if (!activeFindingCode || !findings.some(function (f) { return f.code === activeFindingCode; })) {
            activeFindingCode = findings[0].code;
        }

        findingListEl.innerHTML = findings.map(findingListItemHTML).join('');
        var active = findings.filter(function (f) { return f.code === activeFindingCode; })[0];
        findingDetailEl.innerHTML = findingDetailHTML(active);
    }

    // ---------------------------------------------------------------- actions

    function decisionBadge(decision) {
        if (decision === 'ACCEPTED') return '<span class="ai-badge ai-decision-accepted">APPROVED</span>';
        if (decision === 'DISMISSED') return '<span class="ai-badge ai-decision-dismissed">DISMISSED</span>';
        return '';
    }

    function actionFooter(action) {
        var decision = action.decision;
        var dismissLabel = decision === 'DISMISSED' ? 'Restore to pending' : 'Discard action';
        var approveLabel = decision === 'ACCEPTED' ? 'Revert to pending' : 'Approve action';
        var dismissNext = decision === 'DISMISSED' ? 'NEW' : 'DISMISSED';
        var approveNext = decision === 'ACCEPTED' ? 'NEW' : 'ACCEPTED';

        return '<div class="ai-action-footer">' +
            '<button class="ai-btn ai-btn-outline ai-btn-danger" data-ai-decision="' +
                esc(action.code) + '" data-ai-decision-value="' + dismissNext + '">' +
                esc(dismissLabel) + '</button>' +
            '<button class="ai-btn ai-btn-outline" data-ai-edit="' + esc(action.code) + '">' +
                'Edit action</button>' +
            '<button class="ai-btn ai-btn-success" data-ai-decision="' + esc(action.code) +
                '" data-ai-decision-value="' + approveNext + '">' + esc(approveLabel) + '</button>' +
        '</div>';
    }

    function actionCard(action, index, total) {
        var m = action.metrics || {};
        var where = (action.where || []).map(function (place) {
            return '<code>' + esc(place) + '</code>';
        }).join(' ');
        var resolves = (action.resolves || []).map(function (code) {
            return '<button class="ai-link" data-ai-finding="' + esc(code) + '">' + esc(code) + '</button>';
        }).join(', ');
        var dismissedCls = action.decision === 'DISMISSED' ? ' ai-action-dismissed' : '';

        return '<article class="ai-card-item ai-action' + dismissedCls + '" id="action-' + esc(action.code) + '">' +
            '<div class="ai-move-col">' +
                '<button class="ai-move-btn" data-ai-move="up" data-ai-move-id="' + esc(action.code) +
                    '"' + (index === 0 ? ' disabled' : '') + ' title="Move up">' +
                    '<span class="material-symbols-outlined">arrow_drop_up</span></button>' +
                '<button class="ai-move-btn" data-ai-move="down" data-ai-move-id="' + esc(action.code) +
                    '"' + (index === total - 1 ? ' disabled' : '') + ' title="Move down">' +
                    '<span class="material-symbols-outlined">arrow_drop_down</span></button>' +
            '</div>' +
            '<div class="ai-card-body">' +
            '<header class="ai-card-head">' +
                '<span class="ai-code">' + esc(action.code) + '</span>' +
                '<h3>' + esc(action.title) + '</h3>' +
                decisionBadge(action.decision) +
                '<span class="' + priorityBadgeClass(action.priority_band) + '">PRIORITY: ' +
                    esc(action.priority_band) + '</span>' +
            '</header>' +
            '<p class="ai-observation">' + esc(action.description) + '</p>' +
            (where ? '<div class="ai-where"><strong>Where:</strong>' + where + '</div>' : '') +
            '<div class="ai-stats">' +
                '<span class="ai-stat-help" tabindex="0" data-help="' + esc(IMPACT_HELP) + '">' +
                    'impact <strong>' + esc(m.impact) + '</strong>' +
                    '<span class="material-symbols-outlined ai-stat-info">info</span>' +
                '</span>' +
                (resolves ? '<span>resolves ' + resolves + '</span>' : '') +
            '</div>' +
            actionFooter(action) +
            '</div>' +
            '</article>';
    }

    function renderActionQueue(data) {
        var actions = data.actions || [];
        var findings = data.findings || [];
        var busy = data.status === 'RUNNING' || data.status === 'PENDING';

        actionQueueEl.innerHTML = actions.length
            ? actions.map(function (action, index) {
                return actionCard(action, index, actions.length);
            }).join('')
            : (busy ? '' : emptyBox(
                findings.length
                    ? 'No actions were generated for the findings above.'
                    : 'No actions — there are no findings to act on.'));
    }

    function planItemHTML(action, index) {
        var resolves = (action.resolves || []).join(', ');
        return '<div class="plan-item" data-ai-action-jump="' + esc(action.code) + '">' +
            '<span class="plan-rank">' + (index + 1) + '</span>' +
            '<div class="plan-item-body">' +
                '<span class="plan-item-title">' + esc(action.title) + '</span>' +
                '<span class="plan-item-chips">' + esc(action.code) +
                    (resolves ? ' · resolves ' + esc(resolves) : '') + '</span>' +
            '</div>' +
            '<span class="' + priorityBadgeClass(action.priority_band) + '">' +
                esc(action.priority_band) + '</span>' +
        '</div>';
    }

    function renderPlanPanel(data) {
        // O plano e o conjunto de actions ja aprovadas pelo gestor — nao a fila inteira.
        var actions = (data.actions || []).filter(function (a) { return a.decision === 'ACCEPTED'; });
        if (!actions.length) {
            planPanelEl.innerHTML =
                '<h3>Action Plan</h3>' +
                '<div class="plan-portal">' + esc(portalName()) + '</div>' +
                emptyBox('No approved actions yet. Approve actions in the queue to build the plan.');
            return;
        }

        var high = actions.filter(function (a) { return a.priority_band === 'HIGH'; }).length;
        var rows = actions.map(planItemHTML).join('');
        var note = data.formulas && data.formulas.priority
            ? '<p class="plan-note">' + esc(data.formulas.priority) + '</p>' : '';

        planPanelEl.innerHTML =
            '<h3>Action Plan</h3>' +
            '<div class="plan-portal">' + esc(portalName()) + '</div>' +
            '<div class="plan-meta">' + actions.length + (actions.length === 1 ? ' action' : ' actions') +
                (high ? ' · ' + high + ' high priority' : '') + '</div>' +
            '<div class="plan-list">' + rows + '</div>' +
            '<button class="ai-btn ai-export-btn" data-ai-export type="button">Export plan (CSV)</button>' +
            note;
    }

    // ---------------------------------------------------------------- export CSV

    function csvField(value) {
        var text = String(value === null || value === undefined ? '' : value);
        return '"' + text.replace(/"/g, '""') + '"';
    }

    function csvRow(values) {
        return values.map(csvField).join(',');
    }

    function exportPlan() {
        if (!lastData) return;
        var actions = (lastData.actions || []).filter(function (a) { return a.decision === 'ACCEPTED'; });
        if (!actions.length) return;

        var header = csvRow(['code', 'title', 'description', 'where', 'impact', 'resolves', 'priority_band', 'decision']);
        var rows = actions.map(function (action) {
            var m = action.metrics || {};
            return csvRow([
                action.code,
                action.title,
                action.description,
                (action.where || []).join('; '),
                m.impact || '',
                (action.resolves || []).join('; '),
                action.priority_band,
                action.decision
            ]);
        });

        // BOM no inicio para o Excel abrir acentos PT-BR corretamente em UTF-8.
        var csv = '﻿' + [header].concat(rows).join('\r\n');
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = url;
        link.download = 'action-plan-' + evaluationId + '.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    // ---------------------------------------------------------------- render geral

    function render(data) {
        lastData = data;
        renderControls(data);
        renderState(data);
        renderFindings(data);
        renderActionQueue(data);
        renderPlanPanel(data);
    }

    // ---------------------------------------------------------------- rede

    // load() e chamado de 4 lugares independentes (poll, pos-generate, visibilitychange,
    // carga inicial) e nada impede que duas requisicoes fiquem em voo ao mesmo tempo. Sem
    // controle de ordem, a resposta mais VELHA podia chegar por ultimo e sobrescrever o
    // estado com dado obsoleto — inclusive cancelando um poll que a chamada mais nova
    // acabara de agendar, travando a tela num status desatualizado. loadSeq resolve isso:
    // so a resposta da ULTIMA chamada emitida e aplicada; respostas de chamadas anteriores
    // sao descartadas em silencio.
    var loadSeq = 0;

    function load(options) {
        var autoStart = options && options.autoStart;
        var seq = ++loadSeq;
        return fetch('/api/ai-analysis/' + evaluationId)
            .then(function (response) {
                if (!response.ok) throw new Error('HTTP ' + response.status);
                return response.json();
            })
            .then(function (data) {
                if (seq !== loadSeq) return; // superada por uma chamada mais recente
                render(data);
                if (data.status === 'RUNNING' || data.status === 'PENDING') {
                    schedulePoll();
                } else {
                    stopPoll();
                    if (autoStart && data.status === 'NONE') generate();
                }
            })
            .catch(function (error) {
                if (seq !== loadSeq) return;
                stopPoll();
                each('[data-ai-state]', function (el) {
                    el.innerHTML = '<div class="ai-note ai-note-error">Could not load the ' +
                        'analysis: ' + esc(error.message) + '</div>';
                });
                console.error('ai-analysis:', error);
            });
    }

    function generate() {
        var body = selectedModel ? JSON.stringify({ model: selectedModel }) : '{}';
        return fetch('/api/ai-analysis/' + evaluationId + '/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body
        })
            .then(function (response) {
                // 409 = ja havia uma execucao em curso; o polling cobre esse caso.
                if (!response.ok && response.status !== 409) {
                    return response.json().then(function (payload) {
                        throw new Error(payload.details || payload.error || ('HTTP ' + response.status));
                    });
                }
                return load();
            })
            .catch(function (error) {
                each('[data-ai-state]', function (el) {
                    el.innerHTML = '<div class="ai-note ai-note-error">Could not start the ' +
                        'analysis: ' + esc(error.message) + '</div>';
                });
                console.error('ai-analysis:', error);
            });
    }

    function schedulePoll() {
        stopPoll();
        pollTimer = setTimeout(function () { load(); }, POLL_MS);
    }

    function stopPoll() {
        if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
    }

    function actionByCode(code) {
        return ((lastData && lastData.actions) || []).filter(function (a) {
            return a.code === code;
        })[0];
    }

    function decideAction(code, decisionValue) {
        var action = actionByCode(code);
        if (!action) return;
        fetch('/api/ai-analysis/' + evaluationId + '/actions/' + action.id, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ decision: decisionValue })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) { render(data); })
            .catch(function (error) { console.error('ai-analysis:', error); });
    }

    function moveAction(code, direction) {
        var action = actionByCode(code);
        if (!action) return;
        fetch('/api/ai-analysis/' + evaluationId + '/actions/' + action.id + '/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ direction: direction })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) { render(data); })
            .catch(function (error) { console.error('ai-analysis:', error); });
    }

    // ---------------------------------------------------------------- modal de edicao

    var editModalEl = null;

    function ensureEditModal() {
        if (editModalEl) return editModalEl;
        editModalEl = document.createElement('div');
        editModalEl.className = 'ai-modal-overlay';
        editModalEl.innerHTML = '<div class="ai-modal ai-card" data-ai-modal-body></div>';
        document.body.appendChild(editModalEl);
        return editModalEl;
    }

    function editModalHTML(action) {
        var m = action.metrics || {};
        return '<header class="ai-card-head">' +
                '<h3>' + esc(action.title) + '</h3>' +
                '<span class="ai-modal-icon" title="Action"><span class="material-symbols-outlined">bolt</span></span>' +
                '<span class="' + priorityBadgeClass(action.priority_band) + '">PRIORITY: ' +
                    esc(action.priority_band) + '</span>' +
            '</header>' +
            '<label class="ai-field">Title' +
                '<input type="text" data-ai-field="title" value="' + esc(action.title) + '"></label>' +
            '<label class="ai-field">Description' +
                '<textarea data-ai-field="description" rows="3">' + esc(action.description) + '</textarea></label>' +
            '<label class="ai-field">Where' +
                '<input type="text" data-ai-field="where" value="' + esc((action.where || []).join(', ')) +
                    '" placeholder="e.g. /support, navbar"></label>' +
            '<div class="ai-modal-stats">' +
                '<div class="ai-modal-stat ai-stat-help" tabindex="0" data-help="' + esc(IMPACT_HELP) + '">' +
                    '<span>Impact <span class="material-symbols-outlined ai-stat-info">info</span></span>' +
                    '<strong>' + esc(m.impact) + '</strong></div>' +
                '<div class="ai-modal-stat"><span>Priority score</span><strong>' + esc(m.priority_score) + '</strong></div>' +
            '</div>' +
            '<div class="ai-modal-resolves"><strong>Resolves:</strong> ' + esc((action.resolves || []).join(', ')) + '</div>' +
            '<div class="ai-action-footer">' +
                '<button class="ai-btn ai-btn-outline" data-ai-modal-cancel type="button">Cancel</button>' +
                '<button class="ai-btn ai-btn-success" data-ai-modal-save type="button">Save changes</button>' +
            '</div>';
    }

    function openEditModal(code) {
        var action = actionByCode(code);
        if (!action) return;
        var modal = ensureEditModal();
        modal.querySelector('[data-ai-modal-body]').innerHTML = editModalHTML(action);
        modal.dataset.aiModalCode = code;
        modal.classList.add('active');
    }

    function closeEditModal() {
        if (editModalEl) editModalEl.classList.remove('active');
    }

    function saveEditModal() {
        if (!editModalEl) return;
        var code = editModalEl.dataset.aiModalCode;
        var action = actionByCode(code);
        if (!action) return;

        var body = editModalEl.querySelector('[data-ai-modal-body]');
        var where = body.querySelector('[data-ai-field="where"]').value
            .split(',')
            .map(function (part) { return part.trim(); })
            .filter(Boolean);

        fetch('/api/ai-analysis/' + evaluationId + '/actions/' + action.id, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: body.querySelector('[data-ai-field="title"]').value,
                description: body.querySelector('[data-ai-field="description"]').value,
                where: where
            })
        })
            .then(function (response) { return response.json(); })
            .then(function (data) {
                render(data);
                closeEditModal();
            })
            .catch(function (error) { console.error('ai-analysis:', error); });
    }

    // Leva a aba Hotspots e para no card daquela pagina. O card so e alvo se existir —
    // a decisao de emitir o link ja foi tomada no render (heatmapLinkHTML).
    function goToHeatmapCard(url) {
        var card = heatmapCardFor(heatmapPage(url));
        if (!card) return;

        goToTab('Hotspots');

        // Filtro de cenario ativo esconde o card (.filtered-out zera altura e opacidade):
        // rolar ate ele nao mostraria nada.
        if (card.classList.contains('filtered-out')) {
            var showAll = document.getElementById('filter-all-scenarios');
            if (showAll && !showAll.checked) {
                showAll.checked = true;
                showAll.dispatchEvent(new Event('change'));
            }
        }

        highlight(card);
    }

    // ---------------------------------------------------------------- heatmap modal

    // Reusa o padrao .ai-modal-overlay/.ai-modal (o mesmo do editor de action, mais
    // abaixo) em vez de introduzir um terceiro sistema de modal.
    var heatmapModalEl = null;

    function ensureHeatmapModal() {
        if (heatmapModalEl) return heatmapModalEl;
        heatmapModalEl = document.createElement('div');
        heatmapModalEl.className = 'ai-modal-overlay';
        heatmapModalEl.innerHTML = '<div class="ai-modal ai-modal-heatmap" data-ai-hm-modal-body></div>';
        document.body.appendChild(heatmapModalEl);
        return heatmapModalEl;
    }

    // A evidencia de heatmap para uma URL, procurando nos findings ja carregados.
    function heatmapEvidenceFor(url) {
        var findings = (lastData && lastData.findings) || [];
        for (var i = 0; i < findings.length; i++) {
            var evidence = findings[i].evidence || [];
            for (var j = 0; j < evidence.length; j++) {
                if (evidence[j].type === 'heatmap' && evidence[j].payload &&
                    evidence[j].payload.url === url) {
                    return evidence[j];
                }
            }
        }
        return null;
    }

    function openHeatmapModal(url) {
        var page = heatmapPage(url);
        var item = heatmapEvidenceFor(url);
        if (!page || !page.image || !item) return;

        var hm = item.payload;
        var modal = ensureHeatmapModal();
        modal.querySelector('[data-ai-hm-modal-body]').innerHTML =
            '<button type="button" class="ai-modal-close" data-ai-hm-close aria-label="Close">' +
                '<span class="material-symbols-outlined">close</span>' +
            '</button>' +
            '<h3 class="ai-modal-heatmap-title">' + esc(url) + '</h3>' +
            '<img src="data:' + esc(page.mime || 'image/jpeg') + ';base64,' + esc(page.image) +
                '" alt="' + esc(heatmapAlt(hm)) + '">' +
            '<p class="ai-modal-heatmap-caption">' +
                esc(hm.interactions) + ' interactions recorded across ' + esc(hm.sessions) +
                ' session' + (hm.sessions === 1 ? '' : 's') +
                ' · <em class="ev-combined">all scenarios combined</em>' +
            '</p>';
        modal.classList.add('active');
    }

    function closeHeatmapModal() {
        if (heatmapModalEl) heatmapModalEl.classList.remove('active');
    }

    // ---------------------------------------------------------------- eventos

    document.addEventListener('click', function (event) {
        var generateBtn = event.target.closest('[data-ai-generate]');
        if (generateBtn) {
            // Existe um botao por aba (renderControls injeta o mesmo HTML nos dois
            // containers .ai-controls). Desabilitar so o clicado deixa o gemeo na outra
            // aba clicavel ate o proximo render(), abrindo espaco para um segundo POST.
            each('[data-ai-generate]', function (el) { el.disabled = true; });
            generate();
            return;
        }

        // Tag "G3 · KSC 12 — ...": abre a diretriz completa num modal, reaproveitando a
        // funcao global ja usada pelo modal de KSC das Evaluated Scenarios (dashboard.html).
        var kscAnchor = event.target.closest('[data-ai-ksc-anchor]');
        if (kscAnchor && typeof window.openAiKscAnchorModal === 'function') {
            window.openAiKscAnchorModal(
                kscAnchor.dataset.kscGuideline,
                kscAnchor.dataset.kscGuidelineTitle,
                kscAnchor.dataset.kscId,
                kscAnchor.dataset.kscTitle,
                kscAnchor.dataset.kscDescription
            );
            return;
        }

        // Chip "View in Evaluated Scenarios": sai da camada de IA e para na linha do KSC
        // dentro da tabela de Key Success Criteria do cenario correspondente.
        var kscScenario = event.target.closest('[data-ai-ksc-scenario]');
        if (kscScenario) {
            goToScenarioKsc(kscScenario.dataset.aiKscScenario);
            return;
        }

        // Item da lista a esquerda: so troca qual finding esta ativo, sem refetch.
        var findingItem = event.target.closest('[data-ai-finding-item]');
        if (findingItem) {
            activeFindingCode = findingItem.dataset.aiFindingItem;
            if (lastData) renderFindings(lastData);
            return;
        }

        // "Resolves: F-01" num action card: muda de aba, seleciona o finding e realca
        // o painel de detalhe — que ja mostra as evidencias sem nenhum colapsavel.
        var findingLink = event.target.closest('[data-ai-finding]');
        if (findingLink) {
            activeFindingCode = findingLink.dataset.aiFinding;
            goToTab('Findings');
            if (lastData) renderFindings(lastData);
            highlight(findingDetailEl);
            return;
        }

        // Rola ate o card correspondente na fila de actions. Serve a dois chamadores: o
        // item do backlog (ja na aba Action Plan, onde goToTab e no-op) e o bloco
        // "Recommended actions" do detalhe de um finding, que precisa trocar de aba.
        var actionJump = event.target.closest('[data-ai-action-jump]');
        if (actionJump) {
            goToTab('Action Plan');
            highlight(document.getElementById('action-' + actionJump.dataset.aiActionJump));
            return;
        }

        if (event.target.closest('[data-ai-export]')) {
            exportPlan();
        }

        // Aprovar / descartar / reverter uma action.
        var decisionBtn = event.target.closest('[data-ai-decision]');
        if (decisionBtn) {
            decideAction(decisionBtn.dataset.aiDecision, decisionBtn.dataset.aiDecisionValue);
            return;
        }

        // Setas de reordenacao manual.
        var moveBtn = event.target.closest('[data-ai-move]');
        if (moveBtn) {
            moveAction(moveBtn.dataset.aiMoveId, moveBtn.dataset.aiMove);
            return;
        }

        // Abrir o modal de edicao.
        var editBtn = event.target.closest('[data-ai-edit]');
        if (editBtn) {
            openEditModal(editBtn.dataset.aiEdit);
            return;
        }

        // "View in Hotspots" de um mapa de calor.
        var hmGoto = event.target.closest('[data-ai-hm-goto]');
        if (hmGoto) {
            goToHeatmapCard(hmGoto.dataset.aiHmGoto);
            return;
        }

        // Miniatura de um mapa de calor: abre a imagem grande.
        var hmExpand = event.target.closest('[data-ai-hm-expand]');
        if (hmExpand) {
            openHeatmapModal(hmExpand.dataset.aiHmExpand);
            return;
        }
        if (event.target.closest('[data-ai-hm-close]')) {
            closeHeatmapModal();
            return;
        }
        if (heatmapModalEl && event.target === heatmapModalEl) {
            closeHeatmapModal();
            return;
        }

        // Modal: cancelar, salvar, ou clicar fora do card fecha.
        if (event.target.closest('[data-ai-modal-cancel]')) {
            closeEditModal();
            return;
        }
        if (event.target.closest('[data-ai-modal-save]')) {
            saveEditModal();
            return;
        }
        if (editModalEl && event.target === editModalEl) {
            closeEditModal();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') closeHeatmapModal();
    });

    document.addEventListener('change', function (event) {
        var select = event.target.closest('[data-ai-model]');
        if (!select) return;
        selectedModel = select.value;
        // Os dois seletores (uma aba cada) andam juntos.
        each('[data-ai-model]', function (el) { el.value = selectedModel; });
    });

    // Para de consultar quando a aba do navegador some — nao adianta gastar
    // requisicao com a pagina em segundo plano.
    document.addEventListener('visibilitychange', function () {
        if (document.hidden) stopPoll();
        else load();
    });

    load({ autoStart: true });
})();
