class Stats:
    def __init__(self, total_mutants: int):
        self.total_mutants = total_mutants
        self.killed_mutants = set()
        self.skipped_mutants = set()
        self.survived_mutants = set()

    def add_killed(self, mutant) -> None:
        self.killed_mutants.add(mutant)
    
    def add_survived(self, mutant) -> None:
        self.survived_mutants.add(mutant)

    def add_skipper(self, mutant) -> None:
        self.skipped_mutants.add(mutant)

    def get_killed_count(self) -> int:
        return len(self.killed_mutants)

    def get_skipped_count(self) -> int:
        return len(self.skipped_mutants)

    def get_survived_count(self) -> int:
        return len(self.survived_mutants)

    def get_total_count(self) -> int:
        return len(self.killed_mutants) + len(self.skipped_mutants) + len(self.survived_mutants)

    def checked_all_mutants(self) -> bool:
        # print(self.get_total_count(), self.total_mutants)
        return self.get_total_count() == self.total_mutants