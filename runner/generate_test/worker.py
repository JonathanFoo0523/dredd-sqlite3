from runner.common.types import MutantID
from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST
# from runner.common.async_utils import subprocess_run
import os
import subprocess
import tempfile
import time

class TestGenerationWorker:
    def __init__(self, tracking_binary: str, mutation_binary: str):
        self.tracking_binary = tracking_binary
        self.mutation_binary = mutation_binary

    def get_mutations_in_coverage_by_log(self, statements_path: str):
        with open(statements_path, 'rb') as f:
            statements = f.read()

        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-coverage') as temp_coverage_file:
            env_copy = os.environ.copy()
            env_copy["DREDD_MUTANT_TRACKING_FILE"] = temp_coverage_file.name
            try:
                with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
                    proc_result = subprocess.run([self.tracking_binary, temp_db.name], input=statements, env=env_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception as err:
                print(err)
                exit(1)

            temp_coverage_file.seek(0)
            covered_mutants = sorted([int(line.rstrip()) for line in temp_coverage_file])
        
        return set(covered_mutants), proc_result

    def generate_random_testcases(self):
        pass

    # return True is results is probably deterministics and mutated sqlite give different result compared to unmutated
    # Consider timeout on mutated version  as different
    def differential_oracle(self, mutation_id: int, statements_path: str, expected_result=None) -> bool:
        with open(statements_path, 'rb') as f:
            statements = f.read()

        env_copy = os.environ.copy()
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            start_time = time.time()
            proc_ref = subprocess.run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            end_time = time.time()
            base_time = end_time - start_time

        if expected_result is not None and proc_ref != expected_result:
            print("Indeterministic test result")
            return False

        env_copy["DREDD_ENABLED_MUTATION"] = str(mutation_id)
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            proc_mut = subprocess.run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST)

        return proc_ref.returncode != proc_mut.returncode or proc_ref.stdout != proc_mut.stdout or proc_ref.stderr != proc_mut.stderr

    

    


with tempfile.NamedTemporaryFile(prefix='sqlite-test-temp') as logfile:
    logfile.write('CREATE TABLE a(b);\n'.encode())
    logfile.write('ALTER TABLE a RENAME TO c;\n'.encode())
    logfile.write("UPDATE c SET(d, d) = (7, 'c8320d45');\n".encode())

    logfile.seek(0)

    res = TestGenerationWorker('/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_mutations').differential_oracle(69, logfile.name)
    print(res)


# killed = set([from previous])
# for log in logs:
#     Run coverage tracking
#     for mutant in covered_mutants:
#         if mutant in killed:
#             continue
        
#         Run differential Test

    