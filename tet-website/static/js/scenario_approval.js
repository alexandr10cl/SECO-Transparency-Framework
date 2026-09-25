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
    var STAGE_LABEL = { mapeamento: 'Mapping call', adaptacao: 'Adaptation call' };

    function formatProgressEvent(e) {
        var stage = STAGE_LABEL[e.stage] || e.stage || '';
        var prefix = stage ? '[' + esc(stage) + '] ' : '';
        switch (e.event) {
            case 'attempt':
                return prefix + 'Trying ' + esc(e.model) + ' — attempt ' + e.attempt + '/' + e.attempts_max;
            case 'retry_wait':
                return prefix + esc(e.model) + ' failed (code ' + esc(e.code) + ') — retrying in ' + e.wait_s + 's';
            case 'model_failed':
                return prefix + esc(e.model) + ' unavailable after attempt ' + e.attempt +
                    (e.code ? ' (code ' + esc(e.code) + ')' : '') + ' — moving to the next model';
            case 'model_switch':
                return prefix + 'Switched model: ' + esc(e.from) + ' → ' + esc(e.to);
            case 'success':
                return prefix + esc(e.model) + ' responded on attempt ' + e.attempt;
            case 'chain_exhausted':
                return prefix + 'No model responded (tried: ' + (e.chain || []).map(esc).join(', ') + ')';
            default:
                return prefix + e.event;
        }
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
            html += '<div class="scenario-progress">' +
                events.map(function (e) {
                    return '<div class="scenario-progress-line">' + formatProgressEvent(e) + '</div>';
                }).join('') +
                '</div>';
        }

        var stageResults = computeStageResults(events);
        var modelLines = STAGE_ORDER
            .filter(function (stage) { return stageResults[stage]; })
            .map(function (stage) {
                var r = stageResults[stage];
                return esc(STAGE_LABEL[stage]) + ': ' + esc(r.model) + ' (attempt ' + r.attempt + ')';
            });

        if (modelLines.length) {
            html += '<p class="scenario-progress-summary">' + modelLines.join(' · ') + '</p>';
        } else if (s.model && !isBusy) {
            // Cenarios gerados antes deste log de progresso existir - so tem o
            // modelo agregado (chamada de adaptacao), sem o detalhe por etapa.
            html += '<p class="scenario-progress-summary">Model: ' + esc(s.model) + '</p>';
        }

        if (s.ai_duration_s !== null && s.ai_duration_s !== undefined) {
            var switches = (s.model_switches === null || s.model_switches === undefined) ? '—' : s.model_switches;
            html += '<p class="scenario-progress-summary">' +
                'Total time: ' + Number(s.ai_duration_s).toFixed(1) + 's' +
                ' · Model switches: ' + switches +
                '</p>';
        }

        if (!isBusy && events.length) {
            html += '<details class="scenario-details"><summary>AI call log (' + events.length + ' event(s))</summary>' +
                '<div class="scenario-progress scenario-progress-log">' +
                events.map(function (e) {
                    return '<div class="scenario-progress-line">' + formatProgressEvent(e) + '</div>';
                }).join('') +
                '</div></details>';
        }

        return html;
    }

    // RF22/RNF05: log de origem - de onde veio o cenario e o historico de decisoes
    // do gestor sobre ele. Mesma tela da aprovacao (CLAUDE.md: nao precisa de
    // interface separada), so como uma secao retratil a mais no cartao.
    function renderOriginLog(s) {
        var hasContent = (s.justificativas && s.justificativas.length) ||
            (s.approval_history && s.approval_history.length) || s.cenario_base_title_snapshot;
        if (!hasContent) return '';

        var html = '<details class="scenario-details scenario-origin-log"><summary>Origin log</summary>';

        html += '<div class="scenario-origin-block">';
        html += '<div class="scenario-origin-label">Generated from</div>';
        html += '<div class="scenario-origin-value">Base scenario: "' + esc(s.task_title) + '"' +
            (s.cenario_base_title_snapshot && s.cenario_base_title_snapshot !== s.task_title
                ? ' <span class="scenario-meta-inline">(title at generation time: "' + esc(s.cenario_base_title_snapshot) + '")</span>'
                : '') + '</div>';
        if (s.manager_description_snapshot) {
            html += '<div class="scenario-origin-value">Portal description used: "' + esc(s.manager_description_snapshot) + '"</div>';
        }
        if (s.generated_at) {
            html += '<div class="scenario-origin-value">Generated on ' + formatDate(s.generated_at) +
                (s.model ? ' using ' + esc(s.model) : '') + '</div>';
        }
        html += '</div>';

        if (s.justificativas && s.justificativas.length) {
            html += '<div class="scenario-origin-block">' +
                '<div class="scenario-origin-label">Resources confirmed against the collected data</div>' +
                renderList(s.justificativas, function (j) {
                    return '<strong>' + esc(j.recurso) + '</strong> <span class="scenario-meta-inline">— found in ' + esc(j.fonte) + '</span>';
                }) + '</div>';
        }

        if (s.approval_history && s.approval_history.length) {
            html += '<div class="scenario-origin-block">' +
                '<div class="scenario-origin-label">Review history</div>' +
                renderList(s.approval_history, function (h) {
                    return '<strong>' + esc(DECISION_LABEL[h.decision] || h.decision) + '</strong> by ' +
                        esc(h.reviewer || '—') + ' on ' + formatDate(h.decided_at) +
                        (h.comment ? ' — “' + esc(h.comment) + '”' : '');
                }) + '</div>';
        }

        html += '</details>';
        return html;
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
                    s.etapas_omitidas.length + ' step(s) omitted — no matching resource on the portal</summary>' +
                    renderList(s.etapas_omitidas, function (o) {
                        return '<strong>' + esc(o.etapa) + '</strong> — ' + esc(o.motivo);
                    }) + '</details>';
            }

            if (s.recursos_removidos_validacao && s.recursos_removidos_validacao.length) {
                html += '<details class="scenario-details"><summary>' +
                    s.recursos_removidos_validacao.length + ' resource(s) removed during validation</summary>' +
                    renderList(s.recursos_removidos_validacao, function (r) {
                        return '<strong>' + esc(r.recurso) + '</strong> — ' + esc(r.motivo);
                    }) + '</details>';
            }
        }

        if (s.status === 'AWAITING_APPROVAL') {
            html += '<div class="scenario-actions">' +
                '<button type="button" class="scenario-btn scenario-btn-approve" data-action="approve" data-task-id="' + s.task_id + '">Approve</button>' +
                '<button type="button" class="scenario-btn scenario-btn-reject" data-action="reject" data-task-id="' + s.task_id + '">Reject &amp; regenerate</button>' +
                '</div>' +
                '<div class="scenario-reject-form" data-task-id="' + s.task_id + '" hidden>' +
                '<textarea class="scenario-reject-comment" placeholder="Optional: why is this scenario being rejected?"></textarea>' +
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
