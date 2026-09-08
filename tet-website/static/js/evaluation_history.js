// Historico de avaliacoes — evolucao do overall score do gestor ao longo do tempo.
//
// O tooltip e HTML, e nao o do Chart.js: o padrao da biblioteca (retangulo preto
// translucido, linhas empilhadas) nao pertence a este sistema visual, que e branco,
// de cantos suaves e sombras leves.
(function () {
    var card = document.getElementById('evaluationHistoryCard');
    if (!card) return;

    var canvas = document.getElementById('evaluationHistoryChart');
    var tooltipEl = document.getElementById('historyTooltip');

    var PRIMARY = '#2563eb';
    var AXIS_TEXT = '#a3a3a3';      // --text-tertiary
    var GRID_LINE = 'rgba(0, 0, 0, 0.06)';
    var FONT_SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    function formatDate(iso) {
        if (!iso) return '';
        var date = new Date(iso);
        if (isNaN(date.getTime())) return '';
        return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
    }

    function esc(value) {
        return String(value === null || value === undefined ? '' : value)
            .replace(/[&<>"]/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
            });
    }

    function hideTooltip() {
        tooltipEl.classList.remove('is-visible');
    }

    function showTooltip(point, x, y) {
        var date = formatDate(point.date);
        tooltipEl.innerHTML =
            '<span class="history-tooltip-portal">' + esc(point.portal) + '</span>' +
            '<span class="history-tooltip-name">' + esc(point.name) + '</span>' +
            '<span class="history-tooltip-score">' +
                '<strong>' + point.score + '<span class="history-tooltip-max">/100</span></strong>' +
                (date ? '<span class="history-tooltip-date">' + esc(date) + '</span>' : '') +
            '</span>';
        tooltipEl.style.left = x + 'px';
        tooltipEl.style.top = y + 'px';
        tooltipEl.classList.add('is-visible');
    }

    function render(points) {
        var ctx = canvas.getContext('2d');

        // Preenchimento suave sob a linha, para dar corpo a serie sem pesar.
        var gradient = ctx.createLinearGradient(0, 0, 0, 180);
        gradient.addColorStop(0, 'rgba(37, 99, 235, 0.14)');
        gradient.addColorStop(1, 'rgba(37, 99, 235, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                // Rotulo do eixo e o portal; o nome da avaliacao fica no tooltip, que e
                // onde ele desambigua duas avaliacoes do mesmo portal.
                labels: points.map(function (p) { return p.portal; }),
                datasets: [{
                    label: 'Overall score',
                    data: points.map(function (p) { return p.score; }),
                    borderColor: PRIMARY,
                    backgroundColor: gradient,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: PRIMARY,
                    pointBorderWidth: 2,
                    pointHoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: { padding: { top: 8, bottom: 0, left: 0, right: 8 } },
                // Uma unica entrada, na carga.
                animation: { duration: 600, easing: 'easeOutQuart' },
                interaction: { mode: 'nearest', intersect: false },
                onClick: function (event, elements) {
                    if (!elements.length) return;
                    var point = points[elements[0].index];
                    if (point) window.location.href = '/eval_dashboard/' + point.evaluation_id;
                },
                onHover: function (event, elements) {
                    event.native.target.style.cursor = elements.length ? 'pointer' : 'default';
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: false,  // substituido pelo tooltip HTML
                        external: function (context) {
                            var model = context.tooltip;
                            if (!model.opacity || !model.dataPoints || !model.dataPoints.length) {
                                hideTooltip();
                                return;
                            }
                            var point = points[model.dataPoints[0].dataIndex];
                            if (point) showTooltip(point, model.caretX, model.caretY);
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Evaluated portal (oldest to newest)',
                            color: AXIS_TEXT,
                            font: { family: FONT_SANS, size: 11 },
                            padding: { top: 6 }
                        },
                        grid: { display: false },
                        border: { color: GRID_LINE },
                        ticks: {
                            color: AXIS_TEXT,
                            font: { family: FONT_SANS, size: 11 },
                            maxRotation: 0,
                            autoSkipPadding: 12
                        }
                    },
                    y: {
                        // Escala fixa 0-100: e o que mantem duas avaliacoes comparaveis a
                        // olho. Autoescala transformaria 3 pontos de diferenca num salto.
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Overall score',
                            color: AXIS_TEXT,
                            font: { family: FONT_SANS, size: 11 }
                        },
                        grid: { color: GRID_LINE, drawTicks: false },
                        border: { display: false },
                        ticks: {
                            stepSize: 25,
                            color: AXIS_TEXT,
                            font: { family: FONT_SANS, size: 11 },
                            padding: 8
                        }
                    }
                }
            }
        });

        canvas.addEventListener('mouseleave', hideTooltip);
    }

    fetch('/api/evaluation-history')
        .then(function (response) {
            if (!response.ok) throw new Error('status ' + response.status);
            return response.json();
        })
        .then(function (data) {
            var points = (data && data.points) || [];
            // Sem nenhum score ainda a faixa nao aparece: um grafico vazio no topo da
            // tela ocuparia espaco sem dizer nada.
            if (!points.length) return;

            card.hidden = false;
            render(points);
        })
        .catch(function (error) {
            console.error('Error loading evaluation history:', error);
        });
})();
