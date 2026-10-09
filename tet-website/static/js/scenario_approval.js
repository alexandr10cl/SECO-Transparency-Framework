// Aprovacao de cenarios personalizados (Fase 4 da personalizacao com IA).
//
// Um cartao por task selecionada, dentro do card "Procedures & Scenarios" que
// eval.html ja renderiza. Enquanto a coleta do portal ou a geracao de algum
// cenario ainda estiver rodando, entra em polling - mesmo padrao de
// ai_analysis.js (fetch -> render -> setTimeout se ainda nao terminou).
//
// RNF07: nunca mostra o JSON cru - `cenario_personalizado`, `etapas_omitidas`
// e `recursos_removidos_validacao` sao sempre traduzidos para texto/listas
// legiveis antes de entrar no DOM.

(function () {
    var idEl = document.getElementById('id-avaliacao');
    if (!idEl) return;

    var evaluationId = idEl.textContent.trim();
    var POLL_MS = 4000;
    var pollTimer = null;

    function esc(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/[&<>"]/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
            });
    }

    var STATUS_LABEL = {
        PENDING: 'Waiting for portal collection…',
        RUNNING: 'Generating personalized scenario…',
        AWAITING_APPROVAL: 'Awaiting your approval',
        APPROVED: 'Approved',
        ERROR: 'Generation failed'
    };

    var STATUS_CLASS = {
        PENDING: 'scenario-badge scenario-badge-pending',
        RUNNING: 'scenario-badge scenario-badge-running',
        AWAITING_APPROVAL: 'scenario-badge scenario-badge-review',
        APPROVED: 'scenario-badge scenario-badge-approved',
        ERROR: 'scenario-badge scenario-badge-error'
    };

    function formatDate(iso) {
        if (!iso) return '—';
        var date = new Date(iso);
        return isNaN(date.getTime()) ? iso : date.toLocaleString();
    }

    function renderList(items, formatter) {
        if (!items || !items.length) return '';
        return '<ul class="scenario-sublist">' +
            items.map(function (item) { return '<li>' + formatter(item) + '</li>'; }).join('') +
            '</ul>';
    }

    var DECISION_LABEL = { APPROVED: 'Approved', REJECTED: 'Rejected & regenerated' };

    // Progresso da chamada de IA (services/ai/provider.py:call_ai, eventos gravados
    // por services/scenario_personalization/pipeline.py:_make_progress_logger). Cada
    // objeto tem "event" + "stage" ("mapeamento"/"adaptacao") + campos especificos.
    var STAGE_LABEL = { mapeamento: 'Matching resources', adaptacao: 'Writing the scenario' };
    var STAGE_STEP = { mapeamento: 1, adaptacao: 2 };

    // Codigo HTTP-ish que o provider devolve (providers/base.py:AIProviderError.code)
    // em linguagem de gestor; o codigo cru fica entre parenteses, so pra suporte.
    function describeCode(code) {
        var n = Number(code);
        var reason;
        if (n === 429) reason = 'the AI service is receiving too many requests';
        else if (n === 500 || n === 502 || n === 503) reason = 'the AI service is temporarily overloaded';
        else if (n === 504) reason = 'the AI service took too long to respond';
        else if (n === 401 || n === 403) reason = 'access to the AI service was denied';
        else if (n === 404) reason = 'the model was not found';
        else reason = 'the AI service returned an error';
        return reason + (code ? ' (error ' + esc(code) + ')' : '');
    }

    function modelName(model) {
        return '<span class="ai-log-model">' + esc(model) + '</span>';
    }

    // Um evento de call_ai -> {tone, text}. `tone` pinta o ponto da linha
    // (info/ok/warn/error); `text` ja vem escapado.
    function describeEvent(e) {
        switch (e.event) {
            case 'attempt':
                return e.attempt > 1
                    ? { tone: 'info', text: 'Trying ' + modelName(e.model) + ' again (attempt ' + e.attempt + ' of ' + e.attempts_max + ')' }
                    : { tone: 'info', text: 'Asking ' + modelName(e.model) + '…' };
            case 'retry_wait':
                return { tone: 'warn', text: modelName(e.model) + ' didn’t answer — ' + describeCode(e.code) +
                    '. Trying again in ' + e.wait_s + 's.' };
            case 'model_failed':
                return { tone: 'warn', text: modelName(e.model) + ' couldn’t answer — ' + describeCode(e.code) +
                    '. Moving on to the next model.' };
            case 'model_switch':
                return { tone: 'warn', text: 'Switching from ' + modelName(e.from) + ' to ' + modelName(e.to) };
            case 'success':
                return { tone: 'ok', text: modelName(e.model) + ' answered' +
                    (e.attempt > 1 ? ' (after ' + e.attempt + ' attempts)' : '') };
            case 'chain_exhausted':
                return { tone: 'error', text: 'No model was able to answer (tried: ' +
                    (e.chain || []).map(modelName).join(', ') + ')' };
            default:
                return { tone: 'info', text: esc(e.event) };
        }
    }

    // Uma linha so (barra de progresso, detalhe do que esta rodando agora).
    function formatProgressEvent(e) {
        var stage = STAGE_LABEL[e.stage];
        return (stage ? esc(stage) + ' — ' : '') + describeEvent(e).text;
    }

    function formatElapsed(seconds) {
        if (seconds < 60) return seconds + 's';
        return Math.floor(seconds / 60) + 'm ' + ('0' + (seconds % 60)).slice(-2) + 's';
    }

    // Linha do tempo agrupada por etapa ("Step 1 of 2 · Matching resources"), com o
    // tempo de cada evento desde o primeiro. Substitui a lista monoespacada de
    // "[Mapping call] Trying m — attempt 1/4".
    function renderTimeline(events, isLive) {
        var t0 = Date.parse(events[0].at);
        var lastStage = null;
        var html = '<div class="ai-log' + (isLive ? ' is-live' : '') + '">';
        events.forEach(function (e) {
            if (e.stage && e.stage !== lastStage) {
                html += '<div class="ai-log-stage">Step ' + (STAGE_STEP[e.stage] || '?') + ' of 2 · ' +
                    esc(STAGE_LABEL[e.stage] || e.stage) + '</div>';
                lastStage = e.stage;
            }
            var d = describeEvent(e);
            var t = Date.parse(e.at);
            html += '<div class="ai-log-event is-' + d.tone + '">' +
                '<span class="ai-log-dot"></span>' +
                '<span class="ai-log-text">' + d.text + '</span>' +
                (isNaN(t0) || isNaN(t) ? '' : '<span class="ai-log-time">' + formatElapsed(Math.round((t - t0) / 1000)) + '</span>') +
                '</div>';
        });
        return html + '</div>';
    }

    // Uma chamada de IA por etapa (mapeamento, adaptacao) - cada uma com seu proprio
    // modelo final e tentativa, ja que a cadeia de fallback roda independente em cada
    // uma. Deriva do evento "success" (um por etapa que de fato chamou a API - a
    // adaptacao pode nao ter nenhum, se o mapeamento nao confirmou nenhum recurso).
    var STAGE_ORDER = ['mapeamento', 'adaptacao'];

    function computeStageResults(events) {
        var result = {};
        events.forEach(function (e) {
            if (e.event === 'success' && e.stage) {
                result[e.stage] = { model: e.model, attempt: e.attempt };
            }
        });
        return result;
    }

    // Ao vivo (RUNNING): lista todos os eventos, mais recente por ultimo - a tela
    // atualiza a cada poll (4s). O modelo de cada etapa aparece assim que aquela
    // chamada termina (nao so no final das duas). Terminado: some a lista ao vivo,
    // fica o resumo (modelo por etapa, tempo total, trocas) + o log inteiro dentro
    // de um <details>, pra nao ocupar espaco depois que ja nao importa mais tanto.
    function renderProgress(s) {
        var events = s.progress_log || [];
        var isBusy = s.status === 'PENDING' || s.status === 'RUNNING';
        var html = '';

        if (isBusy && events.length) {
            html += '<div class="scenario-progress">' + renderTimeline(events, true) + '</div>';
        }

        var stageResults = computeStageResults(events);
        var modelLines = STAGE_ORDER
            .filter(function (stage) { return stageResults[stage]; })
            .map(function (stage) {
                var r = stageResults[stage];
                return esc(STAGE_LABEL[stage]) + ': ' + esc(r.model) +
                    (r.attempt > 1 ? ' (after ' + r.attempt + ' attempts)' : '');
            });

        if (modelLines.length) {
            html += '<p class="scenario-progress-summary">' + modelLines.join(' · ') + '</p>';
        } else if (s.model && !isBusy) {
            // Cenarios gerados antes deste log de progresso existir - so tem o
            // modelo agregado (chamada de adaptacao), sem o detalhe por etapa.
            html += '<p class="scenario-progress-summary">Model: ' + esc(s.model) + '</p>';
        }

        if (s.ai_duration_s !== null && s.ai_duration_s !== undefined) {
            var switches = s.model_switches || 0;
            html += '<p class="scenario-progress-summary">' +
                'Took ' + Number(s.ai_duration_s).toFixed(1) + 's' +
                (switches ? ' · switched model ' + switches + (switches === 1 ? ' time' : ' times') : '') +
                '</p>';
        }

        if (!isBusy && events.length) {
            html += '<details class="scenario-details"><summary>AI call log (' + events.length +
                (events.length === 1 ? ' event' : ' events') + ')</summary>' +
                '<div class="scenario-progress scenario-progress-log">' + renderTimeline(events, false) + '</div>' +
                '</details>';
        }

        return html;
    }

    // RF22/RNF05: log de origem - de onde veio o cenario e o historico de decisoes
    // do gestor sobre ele. Mesma tela da aprovacao (CLAUDE.md: nao precisa de
    // interface separada), so como uma secao retratil a mais no cartao.
    function renderOriginLog(s) {
        var hasContent = (s.justificativas && s.justificativas.length) ||
            (s.approval_history && s.approval_history.length) || s.cenario_base_title_snapshot;        if (!hasContent) return '';

        var html = '<details class="scenario-details scenario-origin-log"><summary>Origin log — how this scenario was built</summary>';

        var facts = [['Base scenario', '“' + esc(s.task_title) + '”' +
            (s.cenario_base_title_snapshot && s.cenario_base_title_snapshot !== s.task_title
                ? ' <span class="scenario-meta-inline">(was “' + esc(s.cenario_base_title_snapshot) + '” when generated)</span>'
                : '')]];
        if (s.manager_description_snapshot) {
            facts.push(['Portal description', esc(s.manager_description_snapshot)]);
        }
        if (s.generated_at) {
            facts.push(['Generated', formatDate(s.generated_at) + (s.model ? ' · ' + esc(s.model) : '')]);
        }
        // O que o gestor escreveu ao rejeitar versoes anteriores e foi passado a IA
        // nesta geracao (mesma selecao do pipeline - ver feedback_used em views).
        if (s.feedback_used && s.feedback_used.length) {
            facts.push(['Your feedback', s.feedback_used.map(function (f) {
                return '“' + esc(f) + '”';
            }).join('<br>')]);
        }
        html += '<div class="scenario-origin-block">' +
            '<div class="scenario-origin-label">Generated from</div>' +
            '<dl class="scenario-facts">' +
            facts.map(function (f) { return '<dt>' + f[0] + '</dt><dd>' + f[1] + '</dd>'; }).join('') +
            '</dl></div>';

        if (s.justificativas && s.justificativas.length) {
            html += '<div class="scenario-origin-block">' +
                '<div class="scenario-origin-label">Resources confirmed on the portal</div>' +
                renderItems('confirmed', s.justificativas.map(function (j) {
                    return { name: esc(j.recurso), note: describeSource(j.fonte_legivel) };
                })) + '</div>';
        }

        if (s.approval_history && s.approval_history.length) {
            html += '<div class="scenario-origin-block">' +
                '<div class="scenario-origin-label">Review history</div>' +
                renderItems('history', s.approval_history.map(function (h) {
                    return {
                        name: esc(DECISION_LABEL[h.decision] || h.decision),
                        note: 'By ' + esc(h.reviewer || '—') + ' on ' + formatDate(h.decided_at) +
                            (h.comment ? ' — “' + esc(h.comment) + '”' : '')
                    };
                })) + '</div>';
        }

        html += '</details>';
        return html;
    }

    // Linhas com icone + nome + nota, no lugar das listas com <strong> e travessao.
    // `name` e `note` ja chegam escapados (ou com markup nosso) - ver chamadores.
    var ITEM_ICON = { confirmed: '✓', omitted: '–', removed: '!', history: '•' };

    function renderItems(kind, rows) {
        return '<ul class="scenario-items">' + rows.map(function (r) {
            return '<li class="scenario-item scenario-item-' + kind + '">' +
                '<span class="scenario-item-icon" aria-hidden="true">' + ITEM_ICON[kind] + '</span>' +
                '<div><div class="scenario-item-name">' + r.name + '</div>' +
                (r.note ? '<div class="scenario-item-note">' + r.note + '</div>' : '') +
                '</div></li>';
        }).join('') + '</ul>';
    }

    // `fonte_legivel` vem de validacao.descrever_fonte (backend): so a
    // classificacao - a redacao fica aqui. O caminho cru (paginas_coletadas[16]...)
    // nunca e exibido. A URL vem do portal coletado, entao so vira link se for
    // http(s).
    function describeSource(src) {
        if (!src) return 'Found in the collected portal data';
        switch (src.tipo) {
            case 'pagina':
                var label = esc(src.titulo || src.url || 'a page of the portal');
                if (src.url && /^https?:\/\//i.test(src.url)) {
                    label = '<a href="' + esc(src.url) + '" target="_blank" rel="noopener">' + label + '</a>';
                }
                return 'Found on the page ' + label;
            case 'menu': return 'Found in the portal’s navigation menu';
            case 'link': return 'Found among the links on the portal’s pages';
            case 'metadados': return 'Found in the portal’s metadata';
            default: return 'Found in the collected portal data';
        }
    }

    function renderScenario(s) {
        var isBusy = s.status === 'PENDING' || s.status === 'RUNNING';
        var html = '<div class="scenario-status-row">' +
            '<span class="' + (STATUS_CLASS[s.status] || 'scenario-badge') + '">' +
            (isBusy ? '<span class="scenario-spinner"></span>' : '') +
            esc(STATUS_LABEL[s.status] || s.status) +
            '</span>' +
            (s.guideline_title ? '<span class="scenario-guideline">Guideline: ' + esc(s.guideline_title) + '</span>' : '') +
            '</div>';

        html += renderProgress(s);

        if (s.status === 'ERROR') {
            html += '<p class="scenario-error">Something went wrong generating this scenario. ' +
                'You can try again — the portal data already collected will be reused.</p>' +
                '<button type="button" class="scenario-btn scenario-btn-retry" data-action="retry" data-task-id="' + s.task_id + '">Retry</button>';
            return html;
        }

        if (s.status === 'AWAITING_APPROVAL' || s.status === 'APPROVED') {
            html += '<p class="scenario-text">' + esc(s.cenario_personalizado || '').replace(/\n/g, '<br>') + '</p>';

            if (s.etapas_omitidas && s.etapas_omitidas.length) {
                html += '<details class="scenario-details"><summary>' +
                    s.etapas_omitidas.length + ' step(s) left out — no matching resource on the portal</summary>' +
                    renderItems('omitted', s.etapas_omitidas.map(function (o) {
                        return { name: esc(o.etapa), note: esc(o.motivo) };
                    })) + '</details>';
            }

            // O motivo tecnico (caminho do campo, % de confianca) segue no payload
            // pra auditoria, mas o gestor ve so o que importa: o conteudo coletado
            // nao sustentou o recurso.
            if (s.recursos_removidos_validacao && s.recursos_removidos_validacao.length) {
                html += '<details class="scenario-details"><summary>' +
                    s.recursos_removidos_validacao.length + ' resource(s) removed after validation</summary>' +
                    renderItems('removed', s.recursos_removidos_validacao.map(function (r) {
                        return {
                            name: esc(r.recurso),
                            note: 'The content collected from the portal did not support this resource, ' +
                                'so it was left out of the scenario.'
                        };
                    })) + '</details>';
            }
        }

        if (s.status === 'AWAITING_APPROVAL') {
            html += '<div class="scenario-actions">' +
                '<button type="button" class="scenario-btn scenario-btn-approve" data-action="approve" data-task-id="' + s.task_id + '">Approve</button>' +
                '<button type="button" class="scenario-btn scenario-btn-reject" data-action="reject" data-task-id="' + s.task_id + '">Reject &amp; regenerate</button>' +
                '</div>' +
                '<div class="scenario-reject-form" data-task-id="' + s.task_id + '" hidden>' +
                '<textarea class="scenario-reject-comment" placeholder="Optional: what should be different? This is sent to the AI as guidance for the next version."></textarea>' +
                '<div class="scenario-actions">' +
                '<button type="button" class="scenario-btn scenario-btn-reject-confirm" data-action="reject-confirm" data-task-id="' + s.task_id + '">Confirm rejection</button>' +
                '<button type="button" class="scenario-btn scenario-btn-cancel" data-action="reject-cancel" data-task-id="' + s.task_id + '">Cancel</button>' +
                '</div></div>';
        }

        if (s.status === 'APPROVED') {
            var lastDecision = s.approval_history.length ? s.approval_history[s.approval_history.length - 1] : null;
            if (lastDecision) {
                html += '<p class="scenario-meta">Approved by ' + esc(lastDecision.reviewer || '—') + '</p>';
            }
        }

        html += renderOriginLog(s);

        return html;
    }

    function renderCollectionInfo(collection) {
        var el = document.getElementById('collection-info');
        if (!el) return;

        if (collection.status !== 'DONE' && collection.status !== 'ERROR') {
            el.hidden = true;
            return;
        }

        var html = '<span class="scenario-meta-inline">Portal collection: ' +
            esc(collection.modo_coleta === 'degradado' ? 'degraded' : 'complete');
        if (collection.generated_at) {
            html += ' · collected on ' + formatDate(collection.generated_at);
        }
        html += '</span>';

        if (collection.motivos_degradacao && collection.motivos_degradacao.length) {
            html += renderList(collection.motivos_degradacao, function (m) { return esc(m); });
        }
        if (collection.status === 'ERROR' && collection.error) {
            html += '<p class="scenario-error">Portal collection failed: ' + esc(collection.error) + '</p>';
        }

        el.innerHTML = html;
        el.hidden = false;
    }

    // Stepper de 3 macro-etapas (tela dedicada scenario_status.html - opcional,
    // so atualiza se o elemento existir na pagina). Deriva o passo a partir do
    // que ja temos: nao ha estado granular de "chamada 1 vs chamada 2" no
    // banco (PersonalizedScenario.status so muda quando a geracao inteira da
    // task termina), entao "personalize" fica active enquanto qualquer
    // cenario estiver PENDING/RUNNING, sem distinguir mapeamento de adaptacao.
    function renderStepper(data) {
        var stepper = document.getElementById('pipeline-stepper');
        if (!stepper) return;

        var scenarios = data.scenarios || [];
        var collectionDone = data.collection.status === 'DONE';
        var anyBusy = scenarios.some(function (s) { return s.status === 'PENDING' || s.status === 'RUNNING'; });
        var anyReady = scenarios.some(function (s) { return s.status === 'AWAITING_APPROVAL' || s.status === 'APPROVED'; });

        var status = {
            collect: data.collection.status === 'ERROR' ? 'error' : (collectionDone ? 'done' : 'active'),
            personalize: 'pending',
            review: 'pending'
        };
        if (collectionDone) {
            status.personalize = anyBusy ? 'active' : 'done';
        }
        if (collectionDone && !anyBusy) {
            status.review = data.all_approved ? 'done' : (anyReady ? 'active' : 'pending');
        }

        Object.keys(status).forEach(function (step) {
            var el = stepper.querySelector('.pipeline-step[data-step="' + step + '"]');
            if (!el) return;
            el.classList.remove('is-active', 'is-done', 'is-error');
            if (status[step] !== 'pending') el.classList.add('is-' + status[step]);
        });
    }

    // Barra de progresso unica, juntando scraping e personalizacao (tela dedicada
    // scenario_status.html - opcional, como o stepper). Pesos: a coleta vale
    // COLLECT_WEIGHT da barra e o resto e dividido igualmente entre as 2 chamadas
    // de IA (mapeamento + adaptacao) de cada task.
    //   coleta: collection.progress.visited / .target (estimativa - o alvo sobe
    //           quando a home revela seus links e depois estabiliza)
    //   chamadas: um evento "success" no progress_log do cenario = 1 chamada; um
    //           cenario em estado final conta as 2 (cobre a adaptacao pulada, que
    //           nao emite "success", e o ERROR)
    var COLLECT_WEIGHT = 0.4;
    var CALLS_PER_TASK = 2;
    var FINAL_STATUSES = ['AWAITING_APPROVAL', 'APPROVED', 'ERROR'];

    function computeProgress(data) {
        var collection = data.collection || {};
        var scenarios = data.scenarios || [];

        var collectFrac = 0;
        if (collection.status === 'DONE') {
            collectFrac = 1;
        } else if (collection.progress && collection.progress.target > 0) {
            collectFrac = Math.min(1, collection.progress.visited / collection.progress.target);
        }

        var callsDone = 0;
        scenarios.forEach(function (s) {
            if (FINAL_STATUSES.indexOf(s.status) !== -1) {
                callsDone += CALLS_PER_TASK;
            } else {
                var successes = (s.progress_log || []).filter(function (e) { return e.event === 'success'; }).length;
                callsDone += Math.min(CALLS_PER_TASK, successes);
            }
        });
        var callsTotal = CALLS_PER_TASK * scenarios.length;
        var callsFrac = callsTotal ? callsDone / callsTotal : 0;

        var frac = callsTotal
            ? COLLECT_WEIGHT * collectFrac + (1 - COLLECT_WEIGHT) * callsFrac
            : collectFrac;

        return {
            pct: Math.round(frac * 100),
            collectionFailed: collection.status === 'ERROR',
            // coleta rodando mas ainda sem a primeira pagina registrada
            indeterminate: collection.status !== 'DONE' && collection.status !== 'ERROR' &&
                !(collection.progress && collection.progress.target > 0)
        };
    }

    function describeProgress(data) {
        var collection = data.collection || {};
        var scenarios = data.scenarios || [];

        if (collection.status === 'ERROR') {
            return { text: 'Portal collection failed', detail: '' };
        }
        if (collection.status !== 'DONE') {
            var p = collection.progress;
            if (p && p.target > 0) {
                return {
                    text: 'Collecting portal data — page ' + Math.min(p.visited + 1, p.target) + ' of ~' + p.target,
                    detail: p.url ? esc(p.url) : ''
                };
            }
            return { text: 'Collecting portal data…', detail: '' };
        }

        var index = -1;
        for (var i = 0; i < scenarios.length; i++) {
            if (scenarios[i].status === 'PENDING' || scenarios[i].status === 'RUNNING') { index = i; break; }
        }
        if (index === -1) return { text: 'Done', detail: '' };

        var s = scenarios[index];
        var events = s.progress_log || [];
        return {
            text: 'Personalizing scenario ' + (index + 1) + ' of ' + scenarios.length + ' — ' + s.task_title,
            detail: events.length ? formatProgressEvent(events[events.length - 1]) : 'Waiting to start…'
        };
    }

    function renderProgressBar(data) {
        var bar = document.getElementById('pipeline-progress');
        if (!bar) return;

        var progress = computeProgress(data);
        bar.hidden = !(isPending(data) || progress.collectionFailed);
        if (bar.hidden) return;

        var info = describeProgress(data);
        var fill = document.getElementById('pipeline-progress-fill');
        fill.style.width = progress.pct + '%';
        fill.classList.toggle('is-indeterminate', progress.indeterminate);
        fill.classList.toggle('is-error', progress.collectionFailed);
        document.getElementById('pipeline-progress-pct').textContent = progress.pct + '%';
        // task_title vem do banco: escapado aqui, e "detail" ja vem escapado
        // (formatProgressEvent / esc da URL).
        document.getElementById('pipeline-progress-text').innerHTML = esc(info.text);
        document.getElementById('pipeline-progress-detail').innerHTML = info.detail;
        bar.setAttribute('aria-valuenow', progress.pct);
    }

    function isPending(data) {
        return (data.scenarios || []).some(function (s) {
            return s.status === 'PENDING' || s.status === 'RUNNING';
        }) || data.collection.status === 'PENDING' || data.collection.status === 'RUNNING';
    }

    // So existe no card embutido em eval.html (scenario_status.html ja tem o
    // mesmo aviso como texto estatico na propria pagina, entao o elemento nem
    // existe la - o guard `if (!el) return` cobre isso). Some sozinho assim
    // que a coleta/personalizacao terminar, sem depender de outra visita a
    // pagina.
    function renderTimingNotice(data) {
        var el = document.getElementById('scenario-timing-notice');
        if (!el) return;
        el.hidden = !isPending(data);
    }

    function render(data) {
        renderCollectionInfo(data.collection);
        renderTimingNotice(data);
        renderStepper(data);
        renderProgressBar(data);
        (data.scenarios || []).forEach(function (s) {
            var panel = document.querySelector('.scenario-panel[data-task-id="' + s.task_id + '"]');
            if (!panel) return;
            panel.innerHTML = renderScenario(s);
        });
    }

    function load() {
        fetch('/api/scenarios/' + evaluationId)
            .then(function (res) { return res.json(); })
            .then(function (data) {
                render(data);
                if (pollTimer) { clearTimeout(pollTimer); pollTimer = null; }
                if (isPending(data)) {
                    pollTimer = setTimeout(load, POLL_MS);
                }
            })
            .catch(function () {
                pollTimer = setTimeout(load, POLL_MS);
            });
    }

    function postAction(taskId, action, body) {
        return fetch('/api/scenarios/' + evaluationId + '/' + taskId + '/' + action, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {})
        }).then(function (res) { return res.json(); }).then(render);
    }

    document.addEventListener('click', function (event) {
        var button = event.target.closest('[data-action]');
        if (!button) return;
        var taskId = button.getAttribute('data-task-id');
        var action = button.getAttribute('data-action');

        if (action === 'approve') {
            postAction(taskId, 'approve').then(load);
        } else if (action === 'reject') {
            var form = document.querySelector('.scenario-reject-form[data-task-id="' + taskId + '"]');
            if (form) form.hidden = false;
        } else if (action === 'reject-cancel') {
            var form2 = document.querySelector('.scenario-reject-form[data-task-id="' + taskId + '"]');
            if (form2) form2.hidden = true;
        } else if (action === 'reject-confirm') {
            var form3 = document.querySelector('.scenario-reject-form[data-task-id="' + taskId + '"]');
            var comment = form3 ? form3.querySelector('.scenario-reject-comment').value.trim() : '';
            postAction(taskId, 'reject', { comment: comment }).then(load);
        } else if (action === 'retry') {
            postAction(taskId, 'retry').then(load);
        }
    });

    load();
})();
