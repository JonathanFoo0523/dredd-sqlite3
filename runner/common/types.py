from enum import Enum

MutantID = int

TestStatus = Enum('TestStatus', ['SURVIVED', 'KILLED_TIMEOUT', 'KILLED_FAIL'])

# class TestStatus(Enum):
#     SURVIVED = 1
#     KILL_TIMEOUT = 2
#     KILL_FAIL = 3
