from enum import Enum

class UserType(Enum):
    ADMIN = 'admin'
    SECO_MANAGER = 'seco_manager'
    USER = 'user'

class PerformedTaskStatus(Enum):
    SOLVED = "solved"
    COULDNT_SOLVE = "couldntsolve" 
    NOT_SURE = "notSure"

class NavigationType(Enum):
    PAGE_NAVIGATION = 'PAGE_NAVIGATION'
    TAB_SWITCH = 'TAB_SWITCH'

class AcademicLevel(Enum):
    HIGH_SCHOOL = 'high_school'
    BACHELOR = 'bachelor'
    MASTER = 'master'
    DOCTORATE = 'doctorate'

class PreviousExperience(Enum):
    NEVER = 'never'
    RARELY = 'rarely'
    OFTEN = 'often'
    AWAYS = 'always'

class SegmentType(Enum):
    ACADEMIA = 'academia'
    INDUSTRY = 'industry'
    BOTH = 'both'

class SECOType(Enum):
    OPEN_SOURCE = "OPEN_SOURCE"
    HYBRID = "HYBRID"
    PROPRIETARY = "PROPRIETARY"

class AIAnalysisStatus(Enum):
    """Estado da analise da IA de uma avaliacao. RUNNING funciona como lock:
    enquanto ele estiver posto, schedule() nao submete outra execucao."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"

class AIReviewStatus(Enum):
    """Decisao do gestor sobre um finding ou uma action.

    """
    NEW = "NEW"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    
class StatusCollection(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"

class StatusScenario(Enum):
    """Estado da personalizacao de um cenario (evaluation + task). RUNNING funciona
    como lock, no mesmo esquema de AIAnalysisStatus: enquanto ele estiver posto, o
    pipeline nao dispara outra geracao para o mesmo par evaluation/task."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    ERROR = "ERROR"

class ScenarioApprovalDecision(Enum):
    """Decisao do gestor sobre um PersonalizedScenario, registrada em ScenarioApprovalLog.
    Rejeitar nao e um estado do cenario (ver StatusScenario) - e um evento no historico,
    porque a rejeicao regenera o cenario do zero em vez de deixa-lo parado."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"