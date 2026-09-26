from index import db
from .enums import StatusScenario


class PersonalizedScenario(db.Model):
    """Saida das etapas 3-5 do metodo (personalizacao com IA + validacao automatica),
    uma linha por (evaluation, task). Cada task selecionada na evaluation e um
    cenario-base; este e o resultado da IA ancorando esse cenario-base nos dados
    reais da `portal_collection` correspondente.

    Regenerar (seja por retomada apos erro, seja por rejeicao do gestor na etapa 6)
    sobrescreve esta linha do zero - nao ha edicao parcial. `status == RUNNING` e o
    lock, no mesmo esquema de AIAnalysis/PortalCollection.
    """
    __tablename__ = 'personalized_scenario'
    __table_args__ = (
        db.UniqueConstraint('evaluation_id', 'task_id', name='uq_personalized_scenario_evaluation_task'),
    )

    # Main Rows
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(
        db.Enum(StatusScenario, name="status_scenario_enum"),
        nullable=False,
        default=StatusScenario.PENDING
    )

    # Saida da Chamada 2 (adaptar_etapas) ja com a validacao (etapa 5) aplicada
    cenario_personalizado = db.Column(db.Text, nullable=True)

    # Rastreabilidade da Chamada 1 (mapear_recursos) - schema da saida da etapa 4
    etapas_omitidas = db.Column(db.JSON, nullable=True)
    recursos_confirmados = db.Column(db.JSON, nullable=True)
    justificativas = db.Column(db.JSON, nullable=True)

    # Preenchido pela etapa 5: recursos que a checagem estrutural/de conteudo nao
    # confirmou e por isso foram removidos do cenario_personalizado, com o motivo.
    recursos_removidos_validacao = db.Column(db.JSON, nullable=True)

    # Snapshot dos inputs no momento da geracao - RF22 ("versao do cenario-base") e
    # RNF05 (auditabilidade). Task.title/description e Evaluation.seco_portal_description
    # sao editaveis depois; sem o snapshot o log de origem perderia o que foi
    # realmente usado para gerar esta versao do cenario.
    cenario_base_title_snapshot = db.Column(db.String(100), nullable=True)
    cenario_base_description_snapshot = db.Column(db.Text, nullable=True)
    manager_description_snapshot = db.Column(db.Text, nullable=True)

    # Telemetria (RNF01) - mesmo padrao de AIAnalysis.
    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    tokens_total = db.Column(db.Integer, nullable=True)
    ai_duration_s = db.Column(db.Float, nullable=True)

    # Resumo da cadeia de retry/fallback (services/ai/provider.py:call_ai) desta
    # geracao: quantas vezes o modelo mudou ao todo (mapeamento + adaptacao) e em
    # qual tentativa do modelo final a ULTIMA chamada que rodou teve sucesso.
    model_switches = db.Column(db.Integer, nullable=True)
    final_attempt = db.Column(db.Integer, nullable=True)

    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    generated_at = db.Column(db.DateTime, nullable=True)

    # Log de progresso da chamada de IA em andamento (tentativas, trocas de
    # modelo) - lista de eventos de `services/ai/provider.py:call_ai`, tageados
    # por etapa (mapeamento/adaptacao) em `personalizacao.py`. Reiniciado a
    # cada geracao (ver `_mark_scenario_running`, pipeline.py); a tela do
    # gestor faz poll e mostra isso enquanto RUNNING, e um resumo (tempo
    # total, modelo final, trocas, tentativa final) quando termina.
    progress_log = db.Column(db.JSON, nullable=True)

    # Foreign keys
    evaluation_id = db.Column(db.BigInteger, db.ForeignKey('evaluation.evaluation_id'), nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.task_id'), nullable=False, index=True)
    portal_collection_id = db.Column(db.Integer, db.ForeignKey('portal_collection.id'), nullable=False)

    # Relationships
    evaluation = db.relationship(
        'Evaluation',
        backref=db.backref('personalized_scenarios', lazy=True, cascade='all, delete-orphan')
    )
    task = db.relationship('Task')
    portal_collection = db.relationship(
        'PortalCollection',
        backref=db.backref('personalized_scenarios', lazy=True)
    )

    # Relationship with ScenarioApprovalLog
    approval_log = db.relationship(
        'ScenarioApprovalLog',
        backref=db.backref('scenario', lazy=True),
        cascade='all, delete-orphan',
        order_by='ScenarioApprovalLog.decided_at'
    )
