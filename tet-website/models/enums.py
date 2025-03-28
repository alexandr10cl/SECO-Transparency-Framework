from enum import Enum

class UserType(Enum):
    ADMIN = 'admin'
    SECO_MANAGER = 'seco_manager'
    USER = 'user'

class PerformedTaskStatus(Enum):
    SOLVED = 'solved'
    UNSOLVED = 'unsolved'