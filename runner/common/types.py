type MutantID = int

class TestStatus(Enum):
    SURVIVED = 1
    KILL_TIMEOUT = 2
    KILL_FAIL = 3
