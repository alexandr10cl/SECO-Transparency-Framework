// Developer Journey — RF-02: reconstrução da jornada por participante
(function () {
    const STATUS_LABELS = {
        solved: "Solved",
        "not-sure": "Not sure",
        "couldnt-solve": "Couldn't solve",
    };

    let journeyData = null;
    let journeyFetchPromise = null;
    let activeParticipantRef = null;
    let activeScenarioRef = null;
    let initialized = false;

    function getEvaluationId() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[pathParts.length - 1];
    }

    function formatOffset(seconds) {
        const total = Math.max(0, Math.round(seconds || 0));
        const m = Math.floor(total / 60);
        const s = total % 60;
        return `${m}:${String(s).padStart(2, '0')}`;
    }

    function formatDuration(seconds) {
        const total = Math.max(0, Math.round(seconds || 0));
        const m = Math.floor(total / 60);
        const s = total % 60;
        return `${m}m ${s}s`;
    }

    function formatTimestamp(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        if (Number.isNaN(date.getTime())) return isoString;
        return date.toLocaleString();
    }

    function el(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    function scenarioLabel(ref) {
        const match = /^S(\d+)$/.exec(ref || '');
        return match ? `Scenario ${match[1]}` : ref;
    }

    function fetchJourneyData() {
        if (journeyFetchPromise) return journeyFetchPromise;

        const evaluationId = getEvaluationId();
        journeyFetchPromise = fetch(`/api/developer-journey/${evaluationId}`)
            .then((response) => {
                if (!response.ok) {
                    throw new Error(`Request failed with status ${response.status}`);
                }
                return response.json();
            })
            .then((data) => {
                journeyData = data;
                return data;
            });

        return journeyFetchPromise;
    }

    function renderRoot() {
        const root = document.getElementById('journey-root');
        if (!root) return;

        root.innerHTML = '';

        if (!journeyData || !journeyData.participants || journeyData.participants.length === 0) {
            root.appendChild(el('p', 'loading', 'No participant data yet. The journey appears once developers submit an evaluation.'));
            return;
        }

        const layout = el('div', 'journey-layout');

        const sidebar = el('div', 'journey-sidebar');
        journeyData.participants.forEach((participant) => {
            sidebar.appendChild(buildParticipantCard(participant));
        });
        layout.appendChild(sidebar);

        const detail = el('div', 'journey-detail');
        detail.id = 'journey-detail';
        layout.appendChild(detail);

        root.appendChild(layout);

        if (!activeParticipantRef && journeyData.participants.length > 0) {
            const first = journeyData.participants[0];
            activeParticipantRef = first.participant_ref;
            activeScenarioRef = first.scenarios.length > 0 ? first.scenarios[0].scenario_ref : null;
        }

        updateParticipantSelection();
        renderDetail();
    }

    function buildParticipantCard(participant) {
        const card = el('div', 'journey-participant-card');
        card.dataset.participantRef = participant.participant_ref;

        card.appendChild(el('div', 'journey-participant-id', participant.participant_ref));

        const dots = el('div', 'journey-scenario-dots');
        participant.scenarios.forEach((scenario) => {
            const dot = el('span', `journey-scenario-dot ${scenario.status || ''}`);
            const statusLabel = scenario.status_label || 'Unknown';
            dot.title = `${scenarioLabel(scenario.scenario_ref)} — ${statusLabel}`;
            dots.appendChild(dot);
        });
        card.appendChild(dots);

        card.addEventListener('click', () => {
            activeParticipantRef = participant.participant_ref;
            activeScenarioRef = participant.scenarios.length > 0 ? participant.scenarios[0].scenario_ref : null;
            updateParticipantSelection();
            renderDetail();
        });

        return card;
    }

    function updateParticipantSelection() {
        document.querySelectorAll('.journey-participant-card').forEach((card) => {
            card.classList.toggle('active', card.dataset.participantRef === activeParticipantRef);
        });
    }

    function getActiveParticipant() {
        if (!journeyData) return null;
        return journeyData.participants.find((p) => p.participant_ref === activeParticipantRef) || null;
    }

    function renderDetail() {
        const detail = document.getElementById('journey-detail');
        if (!detail) return;
        detail.innerHTML = '';

        const participant = getActiveParticipant();
        if (!participant) {
            detail.appendChild(el('p', 'journey-empty-state', 'Select a participant to view their journey.'));
            return;
        }

        // Header
        const header = el('div', 'journey-participant-header');

        const avatar = el('div', 'journey-participant-avatar');
        avatar.innerHTML = '<span class="material-symbols-outlined">person</span>';
        header.appendChild(avatar);

        const headerMain = el('div', 'journey-participant-header-main');

        const nameRow = el('div', 'journey-participant-name-row');
        nameRow.appendChild(el('h3', null, participant.participant_ref));
        const scenarioCount = participant.scenarios ? participant.scenarios.length : 0;
        nameRow.appendChild(el('span', 'journey-participant-meta',
            `${scenarioCount} scenario${scenarioCount === 1 ? '' : 's'} performed`));
        headerMain.appendChild(nameRow);

        const fields = el('div', 'journey-profile-fields');
        const profile = participant.profile || {};

        function addStat(icon, title, value, category) {
            if (value === null || value === undefined || value === '') return;
            const item = el('div', `journey-profile-item journey-pill-${category}`);
            const label = el('span', 'journey-profile-label');
            label.appendChild(el('span', 'material-symbols-outlined', icon));
            label.appendChild(el('span', null, title));
            item.appendChild(label);
            item.appendChild(el('span', 'journey-profile-value', String(value)));
            fields.appendChild(item);
        }

        addStat('school', 'Education', profile.academic_level, 'academic');
        addStat('work_history', 'Experience',
            profile.experience_years !== null && profile.experience_years !== undefined
                ? `${profile.experience_years} year${profile.experience_years === 1 ? '' : 's'}`
                : null,
            'experience');
        addStat('domain', 'Segment', profile.segment, 'segment');
        addStat('travel_explore', 'Portal use', profile.portal_familiarity, 'familiarity');

        const sessionDuration = participant.session && participant.session.duration_seconds;
        if (sessionDuration !== undefined && sessionDuration !== null) {
            addStat('schedule', 'Session', formatDuration(sessionDuration), 'session');
        }

        if (!fields.children.length) {
            fields.appendChild(el('span', 'journey-profile-empty', 'No profile data'));
        }

        headerMain.appendChild(fields);
        header.appendChild(headerMain);
        detail.appendChild(header);

        detail.appendChild(el('hr', 'journey-divider'));

        if (!participant.scenarios || participant.scenarios.length === 0) {
            detail.appendChild(el('p', 'journey-no-scenarios', 'This participant has no performed scenarios.'));
            return;
        }

        if (!activeScenarioRef || !participant.scenarios.some((s) => s.scenario_ref === activeScenarioRef)) {
            activeScenarioRef = participant.scenarios[0].scenario_ref;
        }

        // Scenario selector (real buttons: clickable affordance, keyboard accessible)
        const selector = el('div', 'journey-scenario-selector');
        participant.scenarios.forEach((scenario) => {
            const chip = el('button', 'journey-scenario-chip');
            chip.type = 'button';
            if (scenario.scenario_ref === activeScenarioRef) {
                chip.classList.add('active');
            }
            const statusDot = el('span', `journey-status-dot ${scenario.status || ''}`);
            chip.appendChild(statusDot);
            chip.appendChild(document.createTextNode(scenarioLabel(scenario.scenario_ref)));
            chip.addEventListener('click', () => {
                activeScenarioRef = scenario.scenario_ref;
                renderDetail();
            });
            selector.appendChild(chip);
        });
        detail.appendChild(selector);

        detail.appendChild(el('hr', 'journey-divider journey-divider-light'));

        const scenario = participant.scenarios.find((s) => s.scenario_ref === activeScenarioRef);
        if (scenario) {
            detail.appendChild(buildScenarioDetail(scenario));
        }
    }

    function buildScenarioDetail(scenario) {
        const container = document.createDocumentFragment();
        const wrapper = el('div', 'journey-scenario-body');

        const summary = el('div', 'journey-scenario-summary');
        summary.appendChild(el('h4', null, scenario.title));
        const statusLabel = scenario.status_label || STATUS_LABELS[scenario.status] || 'Unknown';
        const statusBadgeClass = scenario.status === 'solved'
            ? 'successful'
            : scenario.status === 'not-sure'
                ? 'partially-successful'
                : 'unsuccessful';
        const badge = el('span', `status-badge ${statusBadgeClass}`);
        badge.appendChild(el('span', 'status-icon', '●'));
        badge.appendChild(document.createTextNode(statusLabel));
        summary.appendChild(badge);
        summary.appendChild(el('span', 'journey-scenario-duration', formatDuration(scenario.duration_seconds)));
        wrapper.appendChild(summary);

        if (scenario.comment) {
            const comment = el('div', 'journey-scenario-comment');
            comment.appendChild(el('strong', null, 'Comment: '));
            comment.appendChild(document.createTextNode(scenario.comment));
            wrapper.appendChild(comment);
        }

        if (!scenario.events || scenario.events.length === 0) {
            wrapper.appendChild(el('p', 'journey-no-events', 'No navigation captured for this scenario.'));
        } else {
            const timeline = el('div', 'journey-timeline');
            scenario.events.forEach((event) => {
                timeline.appendChild(buildEventNode(event));
            });
            wrapper.appendChild(timeline);
        }

        container.appendChild(wrapper);
        return container;
    }

    function buildEventNode(event) {
        const isTabSwitch = event.kind === 'tab_switch';
        const node = el('div', `journey-event${isTabSwitch ? ' tab-switch' : ''}`);

        const offset = el('div', 'journey-event-offset', formatOffset(event.offset_seconds));
        offset.title = formatTimestamp(event.timestamp);
        node.appendChild(offset);

        const titleRow = el('div', 'journey-event-title');
        if (isTabSwitch) {
            titleRow.appendChild(el('span', 'journey-event-kind-pill', 'Tab switch'));
        }
        titleRow.appendChild(document.createTextNode(event.title || event.path || ''));
        node.appendChild(titleRow);

        if (event.url) {
            const link = document.createElement('a');
            link.className = 'journey-event-url';
            link.href = event.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = event.path || event.url;
            node.appendChild(link);
        }

        return node;
    }

    function renderError(message) {
        const root = document.getElementById('journey-root');
        if (!root) return;
        root.innerHTML = '';
        root.appendChild(el('p', 'loading', message));
    }

    function initDeveloperJourneyTab() {
        const navItems = document.querySelectorAll('.dashboard-navbar ul li');
        let journeyTab = null;
        navItems.forEach((item) => {
            if (item.textContent.trim() === 'Developer Journey') {
                journeyTab = item;
            }
        });

        if (!journeyTab) return;

        journeyTab.addEventListener('click', () => {
            if (initialized) return;
            initialized = true;

            fetchJourneyData()
                .then(() => renderRoot())
                .catch((error) => {
                    console.error('Error loading developer journey data:', error);
                    renderError('Unable to load journey data. Please try again later.');
                });
        });
    }

    window.addEventListener('DOMContentLoaded', initDeveloperJourneyTab);
})();
