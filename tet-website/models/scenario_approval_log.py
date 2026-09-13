from index import db
from .enums import ScenarioApprovalDecision


class ScenarioApprovalLog(db.Model):
    """Historico append-only das decisoes do gestor (etapa 6) sobre um
    PersonalizedScenario. Existe como tabela separada, e nao como campo na propria
    scenario, porque rejeitar regenera o cenario do zero (decisao travada no
    metodo) - sem este log, cada rejeicao apagaria o registro da rejeicao anterior
    junto com o cenario que ela reprovou, quebrando a auditabilidade (RNF05) e o
    log de origem (RF22/RF23).
    """
    __tablename__ = 'scenario_approval_log'

    # Main Rows
    id = db.Column(db.Integer, primary_key=True)
    decision = db.Column(db.Enum(ScenarioApprovalDecision, name="scenario_approval_decision_enum"), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=False)

    # Foreign keys
    personalized_scenario_id = db.Column(
        db.Integer,
        db.ForeignKey('personalized_scenario.id'),
        nullable=False,
        index=True
    )
    reviewer_user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    # Relationship with User
    reviewer = db.relationship('User')
