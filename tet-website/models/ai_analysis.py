from index import db
from models import AIAnalysisStatus, AIReviewStatus


# Association Table — uma Action pode resolver varios Findings
ai_action_finding = db.Table('ai_action_finding',
    db.Column('ai_action_id', db.Integer, db.ForeignKey('ai_action.ai_action_id'), primary_key=True),
    db.Column('ai_finding_id', db.Integer, db.ForeignKey('ai_finding.ai_finding_id'), primary_key=True)
)


class AIAnalysis(db.Model):
    """Metadados de uma execucao da analise. Uma linha por avaliacao (regenerar sobrescreve).

    A propria linha e o lock de concorrencia: `status == RUNNING` impede que duas abas
    abertas disparem duas execucoes.
    """
    __tablename__ = 'ai_analysis'

    ai_analysis_id = db.Column(db.Integer, primary_key=True)

    # UNIQUE: uma analise por avaliacao. Regenerar atualiza esta linha e troca os filhos.
    evaluation_id = db.Column(
        db.BigInteger,
        db.ForeignKey('evaluation.evaluation_id'),
        nullable=False,
        unique=True,
        index=True
    )

    status = db.Column(
        db.Enum(AIAnalysisStatus, name='ai_analysis_status_enum'),
        nullable=False,
        default=AIAnalysisStatus.PENDING
    )
    error_message = db.Column(db.Text, nullable=True)

    # Provedor e modelo que efetivamente responderam (a cadeia de fallback pode trocar modelo pedido por outro).
    provider = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(100), nullable=True)

    # Denominador da abrangencia (participantes afetados / total) e, por consequencia, da
    # prioridade. Congelado no momento da geracao: se a avaliacao receber novas sessoes
    # depois, a analise continua coerente consigo mesma em vez de passar a exibir "3/6"
    # numa contagem que nunca foi analisada.
    participants_total = db.Column(db.Integer, nullable=True)

    tokens_total = db.Column(db.Integer, nullable=True)
    # Segundos gastos esperando o modelo, somando as duas etapas (findings e actions). Nao
    # inclui montagem do contexto nem persistencia. So telemetria — nao entra em metrica
    # nenhuma; existe para o gestor ver o custo em tempo da geracao.
    ai_duration_s = db.Column(db.Float, nullable=True)

    started_at = db.Column(db.DateTime, nullable=True)
    generated_at = db.Column(db.DateTime, nullable=True)

    # O que a validacao tecnica (fase 4) barrou e por que, mais os findings que nenhuma
    # action cobriu. Serve para iterar no prompt — ver a IA errando e onde. Guarda tambem
    # o tamanho do catalogo de evidencias e do escopo do framework: descrevem a entrada da
    # geracao, nao alimentam metrica nenhuma, entao nao justificam coluna propria.
    debug = db.Column(db.JSON, nullable=True)

    evaluation = db.relationship(
        'Evaluation',
        backref=db.backref('ai_analysis', uselist=False, cascade='all, delete-orphan')
    )

    findings = db.relationship(
        'AIFinding',
        backref=db.backref('analysis', lazy=True),
        cascade='all, delete-orphan',
        order_by='AIFinding.ai_finding_id'
    )

    actions = db.relationship(
        'AIAction',
        backref=db.backref('analysis', lazy=True),
        cascade='all, delete-orphan',
        order_by='AIAction.ai_action_id'
    )


class AIFinding(db.Model):
    """Um problema de transparencia identificado, ancorado num KSC do framework.

    `title` = qual e o problema; `observation` = o que os dados mostram e por que sustentam esse problema.
    """
    __tablename__ = 'ai_finding'

    ai_finding_id = db.Column(db.Integer, primary_key=True)
    ai_analysis_id = db.Column(
        db.Integer,
        db.ForeignKey('ai_analysis.ai_analysis_id'),
        nullable=False,
        index=True
    )

    title = db.Column(db.String(500), nullable=False)
    observation = db.Column(db.Text, nullable=False)

    # Framework-anchored: a IA escolhe um KSC existente, nunca cria.
    ksc_id = db.Column(
        db.Integer,
        db.ForeignKey('key_success_criterion.key_success_criterion_id'),
        nullable=False
    )

    # Evidencias ja validadas contra o catalogo: [{id, type, participant_id, task_id, summary}].
    # Este e o unico JSON grande do modelo e ele paga o proprio custo — e ao mesmo tempo a
    # entrada das formulas de metrics.py e o conteudo do drill-down ate o dado original
    # Sem ele, cada carregamento de pagina reconstruiria o catalogo inteiro.
    evidence = db.Column(db.JSON, nullable=False)

    review_status = db.Column(
        db.Enum(AIReviewStatus, name='ai_review_status_enum'),
        nullable=False,
        default=AIReviewStatus.NEW
    )

    ksc = db.relationship('Key_success_criterion')


class AIAction(db.Model):
    """Recomendacao concreta de melhoria que trata um ou mais Findings."""
    __tablename__ = 'ai_action'

    ai_action_id = db.Column(db.Integer, primary_key=True)
    ai_analysis_id = db.Column(
        db.Integer,
        db.ForeignKey('ai_analysis.ai_analysis_id'),
        nullable=False,
        index=True
    )

    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # Onde agir: paginas, secoes ou componentes do portal. `where` sozinho e palavra
    # reservada no MySQL — dai o sufixo. Na API o campo continua se chamando "where".
    where_to_act = db.Column(db.JSON, nullable=False)

    decision = db.Column(
        db.Enum(AIReviewStatus, name='ai_review_status_enum'),
        nullable=False,
        default=AIReviewStatus.NEW
    )

    # Posicao manual no plano, definida pelas setas da UI. NULL = segue a ordenacao
    # automatica por priority_score; regenerar a analise recria as actions com NULL.
    manual_rank = db.Column(db.Integer, nullable=True)

    findings = db.relationship(
        'AIFinding',
        secondary=ai_action_finding,
        backref=db.backref('actions', lazy=True),
        order_by='AIFinding.ai_finding_id'
    )
