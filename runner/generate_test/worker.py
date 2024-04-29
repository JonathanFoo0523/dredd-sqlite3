from runner.common.types import MutantID
from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST
# from runner.common.async_utils import subprocess_run
import os
import subprocess
import tempfile
import time

SQLANCER_JAR_PATH = '/home/ubuntu/sqlancer/target/sqlancer-2.0.0.jar'

class TestGenerationWorker:
    def __init__(self, source_name: str, tracking_binary: str, mutation_binary: str):
        self.source_name = source_name
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


    # Note that this generate 100 database at a time, with seeds [random_seed, random_seed+100)
    def generate_random_testcases(self, random_seed: int, temp_dir: str, num_queries: int = 1000, oracle: str= 'FUZZER') -> None:
        try:
            proc = subprocess.run([
                        'java',
                        '-jar',
                        SQLANCER_JAR_PATH,
                        '--random-seed',
                        str(random_seed),
                        '--num-queries',
                        str(num_queries),
                        '--max-generated-databases',
                        '1',
                        'sqlite3',
                        '--oracle',
                        oracle
                    ], cwd=temp_dir, stdout=subprocess.DEVNULL)
        except Exception as err:
            print(err)

    # return True if results is probably deterministics and mutated sqlite give different result compared to unmutated
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

        return self._process_result_is_difference(proc_ref, proc_mut)

    def _process_result_is_difference(self, process1: subprocess.CompletedProcess, process2: subprocess.CompletedProcess) -> bool:
        return process1.returncode != process2.returncode or process1.stdout != process2.stdout or process1.stderr != process2.stderr


    def slice_runner(self, prev_killed: set[MutantID]):
        newly_killed = set()
        while still_testing:
            sqlancer_seed = random.randint(0, 2 ** 32 - 1) // 100
            with tempfile.TemporaryDirectory as sqlancer_temp_dir:
                self.generate_random_testcases(sqlancer_seed, sqlancer_temp_dir)

                for log in sorted(os.listdir(os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3'))):
                    log_path = os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3', log)
                    mutants_in_coverage, cov_result = self.get_mutations_in_coverage_by_log(log_path)

                    for mutant in mutants_in_coverage:
                        if mutant in killed:
                            continue

                        if self.differential_oracle(mutant, log_path, cov_result):
                            print(f"Kill! Mutants killed so far: {len(newly_killed)}")
                            newly_killed.add(mutant)
                            prev_killed.add(mutant)
                            # Possibly copy file

                    print(f"Killed/Remain: {len(sqlancer_killed)}/{len(survivors[file])}, Testing: {m}/{len(mutants_in_coverage)}", end="\r")

    

# with tempfile.NamedTemporaryFile(prefix='sqlite-test-temp') as logfile:
#     logfile.write('CREATE TABLE a(b);\n'.encode())
#     logfile.write('ALTER TABLE a RENAME TO c;\n'.encode())
#     logfile.write("UPDATE c SET(d, d) = (7, 'c8320d45');\n".encode())

#     logfile.seek(0)

#     res = TestGenerationWorker('alter', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_mutations').differential_oracle(70, logfile.name)
#     print(res)

# with tempfile.TemporaryDirectory() as temp_dir:
#     worker = TestGenerationWorker('alter', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_mutations')
#     worker.generate_random_testcases(1, temp_dir)
#     print(sorted(os.listdir(f'{temp_dir}/logs/sqlite3')))


# killed = set([from previous])
# for log in logs:
#     Run coverage tracking
#     for mutant in covered_mutants:
#         if mutant in killed:
#             continue
        
#         Run differential Test

    