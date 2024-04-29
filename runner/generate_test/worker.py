from runner.common.types import MutantID
# from runner.common.async_utils import subprocess_run
import os
import subprocess
import tempfile

class TestGenerationWorker:
    def __init__(self, tracking_binary: str):
        self.tracking_binary = tracking_binary

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

    def generate_random_testcases():
        pass

    def differential_oracle(self, expected_result=None):
        pass


with tempfile.NamedTemporaryFile(prefix='sqlite-test-temp') as logfile:
    logfile.write('CREATE TABLE a(b);\n'.encode())
    logfile.write('ALTER TABLE a RENAME TO c;\n'.encode())
    logfile.write("UPDATE c SET(b, b) = (7, 'c8320d45');\n".encode())

    logfile.seek(0)

    covered, res = TestGenerationWorker('/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking').get_mutations_in_coverage_by_log(logfile.name)
    print(covered)


# killed = set([from previous])
# for log in logs:
#     Run coverage tracking
#     for mutant in covered_mutants:
#         if mutant in killed:
#             continue
        
#         Run differential Test

    