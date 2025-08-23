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
    PAGE_NAVIGATION = 'pageNavigation'
    TAB_SWITCH = 'tabSwitch'

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
    OPEN_SOURCE = "open_source"
    HYBRID = "hybrid"
    PROPRIETARY = "proprietary"