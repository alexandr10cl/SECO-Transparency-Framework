from index import db
from .enums import StatusCollection


class PortalCollection(db.Model):
    """Saida das etapas 1-2 do metodo (scraping + estruturacao), uma linha por
    evaluation. Roda uma unica vez no cadastro do portal (RF21) - regenerar
    sobrescreve esta linha, no mesmo esquema de AIAnalysis: `status == RUNNING`
    e o lock que impede duas execucoes simultaneas para a mesma evaluation.

    `dados_portal` e a saida inteira da etapa 2 (schema fixo do CLAUDE.md do
    projeto de personalizacao): navegacao, paginas coletadas, metadados. E a
    fonte da verdade contra a qual a etapa 5 (validacao) confere as
    justificativas da IA - por isso fica associada aqui, nao dentro de cada
    PersonalizedScenario, que so guarda o resultado da personalizacao.
    """
    __tablename__ = 'portal_collection'

    # Main Rows
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(
        db.Enum(StatusCollection, name="status_collection_enum"),
        nullable=False,
        default=StatusCollection.PENDING
    )

    dados_portal = db.Column(db.JSON, nullable=True)
    modo_coleta = db.Column(db.String(20), nullable=True)  # "completo" | "degradado"
    motivos_degradacao = db.Column(db.JSON, nullable=True)

    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    generated_at = db.Column(db.DateTime, nullable=True)

    # Foreign key to the evaluation table
    evaluation_id = db.Column(
        db.BigInteger,
        db.ForeignKey('evaluation.evaluation_id'),
        nullable=False,
        unique=True
    )

    # Relationship with Evaluation
    evaluation = db.relationship(
        'Evaluation',
        backref=db.backref('portal_collection', uselist=False, cascade='all, delete-orphan')
    )
