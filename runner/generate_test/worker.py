from runner.common.types import MutantID
from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST
from runner.common.counter import Stats

import os
import subprocess
import tempfile
import time
import random
import asyncio
import pickle
from tqdm import tqdm

SQLANCER_JAR_PATH = '/home/ubuntu/sqlancer/target/sqlancer-2.0.0.jar'

class TestGenerationWorker:
    def __init__(self, source_name: str, tracking_binary: str, mutation_binary: str, max_parallel_tasks: int = 1):
        self.source_name = source_name
        self.tracking_binary = tracking_binary
        self.mutation_binary = mutation_binary
        self.max_parallel_tasks = max_parallel_tasks

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
    # Consider timeout on mutated version as different
    def differential_oracle(self, mutation_id: int, statements_path: str, expected_result=None) -> bool:
        with open(statements_path, 'rb') as f:
            statements = f.read()

        env_copy = os.environ.copy()
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            start_time = time.time()
            proc_ref = subprocess.run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            end_time = time.time()
            base_time = end_time - start_time

        if expected_result is not None and self._process_result_is_difference(proc_ref, expected_result):
            print("Indeterministic test result")
            return False

        env_copy["DREDD_ENABLED_MUTATION"] = str(mutation_id)
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            try:
                proc_mut = subprocess.run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST)
            except subprocess.TimeoutExpired:
                return True

        return self._process_result_is_difference(proc_ref, proc_mut)


    def _process_result_is_difference(self, process1: subprocess.CompletedProcess, process2: subprocess.CompletedProcess) -> bool:
        return process1.returncode != process2.returncode or process1.stdout != process2.stdout or process1.stderr != process2.stderr

    # A simple testing condition to ensure a source is run on exactly 100 logs
    def still_testing(self):
        try:
            return self.continue_testing
        except:
            self.continue_testing = False
            return True

    async def mutant_queue_producer(self, sqlancer_temp_dir: str, queue: asyncio.Queue, killed: set[MutantID], in_coverage: set[MutantID], logs: list[str], pbar=None):
        for log in logs:
            log_path = os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3', log)
            mutants, cov_result = self.get_mutations_in_coverage_by_log(log_path)

            in_coverage.update(mutants)
            for mutant in mutants:
                if mutant in killed:
                    continue
                queue.put_nowait((log, cov_result, mutant))

            # with open(self.fuzzing_checkpoint, 'ab+') as f:
            #     pickle.dump({'seed': None, 'coverage': mutant, 'output': cov_result})
            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Covered': len(in_coverage)})



    async def mutant_queue_consumer(self, sqlancer_temp_dir: str, queue: asyncio.Queue, killed: set[MutantID], pbar=None):
        while True:
            log, cov_result, mutant = await queue.get()
            log_path = os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3', log)

            if mutant not in killed and self.differential_oracle(mutant, log_path, cov_result):
                killed.add(mutant)

            # with open(self.generate_checkpoint, 'ab+') as f:
            #     pickle.dump({'seed': None, 'coverage': mutant, 'output': cov_result})

            queue.task_done()
            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Killed': len(killed)})
                


    async def slice_runner(self, killed: set[MutantID]):
        while self.still_testing():
            sqlancer_seed = random.randint(0, 2 ** 32 - 1) // 100 * 100 
            with tempfile.TemporaryDirectory() as sqlancer_temp_dir:
                print(f"Generating test case with seed {sqlancer_seed}")
                self.generate_random_testcases(sqlancer_seed, sqlancer_temp_dir)

                logs = sorted(os.listdir(os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3')))

                newly_killed = set()
                in_coverage = set()
                queue = asyncio.Queue()

                producers_pbar = tqdm(total=len(logs), desc='Finding coverage')
                producers = [asyncio.create_task(self.mutant_queue_producer(sqlancer_temp_dir, queue, killed, in_coverage, logs[i :: self.max_parallel_tasks], producers_pbar)) for i in range(self.max_parallel_tasks)]
                await asyncio.gather(*producers)

                consumer_pbar = tqdm(total=queue.qsize(), desc='Checking Difference')
                consumers = [asyncio.create_task(self.mutant_queue_consumer(sqlancer_temp_dir, queue, killed, consumer_pbar)) for _ in range(self.max_parallel_tasks)]
                await queue.join()

                for task in consumers:
                    task.cancel()

                await asyncio.gather(*consumers, return_exceptions=True)


    

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

a = TestGenerationWorker('alter', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_mutations')
asyncio.run(a.slice_runner(set()))

# killed = set([from previous])
# for log in logs:
#     Run coverage tracking
#     for mutant in covered_mutants:
#         if mutant in killed:
#             continue
        
#         Run differential Test

    