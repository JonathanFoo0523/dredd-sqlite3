from runner.common.types import MutantID, TestStatus
from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST, RANDOM_SQLS_GENERATION_TIMEOUT_SECONDS
from runner.common.counter import Stats
from runner.common.async_utils import subprocess_run, TIMEOUT_RETCODE
from subprocess import CompletedProcess

import os
import subprocess
import tempfile
import time
import random
import asyncio
import pickle
import time
import shutil
import re
from tqdm import tqdm

# SQLANCER_JAR_PATH = '/home/ubuntu/sqlancer/target/sqlancer-2.0.0.jar'

class TestGenerationWorker:
    def __init__(self, sqlancer_jar_path: str, source_name: str, killed: set[MutantID], tracking_binary: str, mutation_binary: str, output_dir: str, max_parallel_tasks: int = 4, total_gen: int = 8):
        assert(os.path.isfile(tracking_binary))
        assert(os.path.isfile(mutation_binary))
        assert(os.path.isdir(output_dir))
        assert(max_parallel_tasks >= 0)

        self.sqlancer_jar_path = sqlancer_jar_path
        self.source_name = source_name
        self.tracking_binary = tracking_binary
        self.mutation_binary = mutation_binary
        self.output_dir = output_dir
        self.max_parallel_tasks = max_parallel_tasks
        self.killed = killed

        # self.fuzzing_checkpoint = os.path.join(output_dir, source_name, 'fuzzing_checkpoint.pkl')
        # self.diffential_checkpoint = os.path.join(output_dir, source_name, 'differential_checkpoint.pkl')

        self.outputfile = os.path.join(output_dir, f'{source_name}_output.csv')

        self.interesting_test_dir = os.path.join(output_dir, 'interesting_test_dir')
        if not os.path.isdir(self.interesting_test_dir):
            os.mkdir(self.interesting_test_dir)

        self.max_running_time = 60 * 60
        self.start_time = time.time()
        self.run_time = 0

        self.gen = 0
        self.total_gen = total_gen

    async def get_mutations_in_coverage_by_log(self, statements_path: str):
        with open(statements_path, 'rb') as f:
            statements = f.read()

        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-coverage') as temp_coverage_file:
            env_copy = os.environ.copy()
            env_copy["DREDD_MUTANT_TRACKING_FILE"] = temp_coverage_file.name
            try:
                with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
                    proc_result = await subprocess_run([self.tracking_binary, temp_db.name], input=statements, env=env_copy, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            except Exception as err:
                print(err)
                return set(), None

            temp_coverage_file.seek(0)
            covered_mutants = sorted([int(line.rstrip()) for line in temp_coverage_file])
        
        proc_result_obj = CompletedProcess(args=[self.tracking_binary, temp_db.name], stdout=proc_result[0], stderr=proc_result[1], returncode=proc_result[2])
        return set(covered_mutants), proc_result_obj


    # Note that this generate 100 database at a time, with seeds [random_seed, random_seed+100)
    def generate_random_testcases(self, random_seed: int, temp_dir: str, num_queries: int = 500, oracle: str= 'FUZZER') -> None:
        try:
            proc = subprocess.run([
                        'java',
                        '-jar',
                        self.sqlancer_jar_path,
                        '--random-seed',
                        str(random_seed),
                        '--num-queries',
                        str(num_queries),
                        '--max-generated-databases',
                        '1',
                        'sqlite3',
                        '--oracle',
                        oracle
                    ], cwd=temp_dir, stdout=subprocess.DEVNULL, timeout=RANDOM_SQLS_GENERATION_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired as timeout_err:
            raise timeout_err
        except Exception as err:
            print(err)

    # return True if results is probably deterministics and mutated sqlite give different result compared to unmutated
    # Consider timeout on mutated version as different
    async def differential_oracle(self, mutation_id: int, statements_path: str, expected_result=None) -> bool:
        with open(statements_path, 'rb') as f:
            statements = f.read()

        env_copy = os.environ.copy()
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            start_time = time.time()
            # try:
            #     proc_ref = await subprocess_run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            # except BrokenPipeError:
            #     pass
            proc_ref = await subprocess_run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            end_time = time.time()
            base_time = end_time - start_time
            proc_ref = CompletedProcess(args=[self.mutation_binary, temp_db.name], stdout=proc_ref[0], stderr=proc_ref[1], returncode=proc_ref[2])

        if expected_result is not None and self._process_result_is_difference(proc_ref, expected_result):
            # print("Indeterministic test result")
            return TestStatus.KILLED_INDETERMINISTIC

        env_copy["DREDD_ENABLED_MUTATION"] = str(mutation_id)
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-test-generation-db', suffix='.db') as temp_db:
            # try:
            # try:
            #     proc_mut = await subprocess_run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST)
            #     proc_mut = CompletedProcess(args=[self.mutation_binary, temp_db.name], stdout=proc_mut[0], stderr=proc_mut[1], returncode=proc_mut[2])
            # except BrokenPipeError:
            #     pass
            proc_mut = await subprocess_run([self.mutation_binary, temp_db.name], input=statements, env=env_copy, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST)
            proc_mut = CompletedProcess(args=[self.mutation_binary, temp_db.name], stdout=proc_mut[0], stderr=proc_mut[1], returncode=proc_mut[2])
            

            if proc_mut.returncode == TIMEOUT_RETCODE:
                return TestStatus.KILLED_TIMEOUT
            # except subprocess.TimeoutExpired:
            #     return TestStatus.KILLED_TIMEOUT

        if self._process_result_is_difference(proc_ref, proc_mut):
            return TestStatus.KILLED_FAILED
        else:
            return TestStatus.SURVIVED


    def _process_result_is_difference(self, process1: subprocess.CompletedProcess, process2: subprocess.CompletedProcess) -> bool:
        return process1.returncode != process2.returncode or process1.stdout != process2.stdout or process1.stderr != process2.stderr

    # def still_testing(self):
    #     return time.time() - self.start_time <= self.max_running_time

    def still_testing(self):
        self.gen += 1
        return self.gen <= self.total_gen

    async def mutant_queue_producer(self, sqlancer_temp_dir: str, queue: asyncio.Queue, in_coverage: set[MutantID], seed_log_lists: list[(int, str)], pbar=None):
        for i, (seed, log) in enumerate(seed_log_lists):
            log_path = os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3', log)
            mutants, cov_result = await self.get_mutations_in_coverage_by_log(log_path)

            in_coverage.update(mutants)
            for mutant in mutants:
                if mutant in self.killed:
                    continue
                queue.put_nowait((log, seed, cov_result, mutant))

            # with open(self.fuzzing_checkpoint, 'ab+') as f:
            #     pickle.dump({'seed': seed, 'coverage': mutants, 'output': cov_result}, f)

            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Covered': len(in_coverage)})


    async def mutant_queue_consumer(self, sqlancer_temp_dir: str, queue: asyncio.Queue, new_kill: dict[MutantID, int], pbar=None):
        while True:
            log, seed, cov_result, mutant = await queue.get()
            log_path = os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3', log)

            if mutant not in self.killed and mutant not in new_kill:
                diffential_result = await self.differential_oracle(mutant, log_path, cov_result)
                if diffential_result == TestStatus.KILLED_FAILED:
                    self.killed.add(mutant)
                    new_kill[mutant] = seed
                    shutil.copyfile(log_path, os.path.join(self.interesting_test_dir, f'database_{seed}.log'))

                with open(self.outputfile, 'a+') as f:
                    f.write(f"{seed}, {mutant}, {diffential_result.name}\n")

                # with open(self.diffential_checkpoint, 'ab+') as f:
                #     pickle.dump({'seed': seed, 'mutant': mutant, 'status': diffential_result.name}, f)

            queue.task_done()
            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Killed': len(new_kill)})

    def load_progress(self) -> (dict[MutantID, int], set[MutantID], set[int]):
        new_kill = dict()
        in_coverage = set()
        tested_seeds = set()

        # Load from gloabl history
        if os.path.isfile(f'{self.output_dir}/fuzzing_test.pkl'):
            with open(f'{self.output_dir}/fuzzing_test.pkl', 'rb') as f:
                try:
                    while True:
                        # pickle.load({'source': self.source_name, 'gen': self.total_gen - self.gen, 'cum_kill': new_kill, 'seeds': tested_seeds, 'cum_coverage': in_coverage}, f)
                        obj = pickle.load(f)
                        if obj['source'] == self.source_name and self.gen < obj['gen']:
                            self.gen = obj['gen']
                            new_kill = obj['cum_kill']
                            in_coverage = obj['cum_coverage']
                            tested_seeds = obj['seeds']
                except EOFError:
                    pass
                
        # Don't Load from local history, give up unfinished differential tests
        # if os.path.isfile(self.diffential_checkpoint):
        #     with open(self.diffential_checkpoint, 'rb') as f:
        #         try:
        #             while True:
        #                 obj = pickle.load(f)
        #                 # seed, mutant, status
        #                 tested_seeds.add(obj['seed'])
        #                 in_coverage.add(obj['mutant'])
        #                 if obj['status'] == TestStatus.KILLED_FAILED:
        #                     new_kill[obj['mutant']] = obj['seed']
        #         except EOFError:
        #             # Ran out of input
        #             pass
                
        return new_kill, in_coverage, tested_seeds

    async def slice_runner(self):
        print("Start differential test:", self.source_name)
        new_kill, in_coverage, tested_seeds = self.load_progress()
        print("continue", len(new_kill))


        if not os.path.isfile(self.outputfile):
            with open(self.outputfile, 'w+') as f:
                f.write(f"seed, mutant, status\n")

        while self.still_testing():
            
            while True:
                sqlancer_seed = random.randint(0, 2 ** 32 - 1) // 100 * 100 
                if sqlancer_seed not in tested_seeds:
                    break

            with tempfile.TemporaryDirectory() as sqlancer_temp_dir:
                print(f"Generating test case with seed {sqlancer_seed}")
                try:
                    self.generate_random_testcases(sqlancer_seed, sqlancer_temp_dir)
                except subprocess.TimeoutExpired:
                    print("Test case generation takes too long. Skip seed")
                    self.gen -= 1
                    continue

                file_re = r'^database(\d+)-cur.log$'
                files_in_dir = os.listdir(os.path.join(sqlancer_temp_dir, 'logs', 'sqlite3'))
                logs = list(filter(lambda s: re.search(file_re, s) is not None, files_in_dir))
                logs.sort(key=lambda s: int(re.search(file_re, s).group(1)))

                seed_log_list = list(zip(range(sqlancer_seed, sqlancer_seed+100), logs))

                queue = asyncio.Queue()

                producers_pbar = tqdm(total=len(logs), desc='Finding coverage')
                producers = [asyncio.create_task(self.mutant_queue_producer(sqlancer_temp_dir, queue, in_coverage, seed_log_list[i :: self.max_parallel_tasks], producers_pbar)) for i in range(self.max_parallel_tasks)]
                await asyncio.gather(*producers)
                producers_pbar.close()

                consumer_pbar = tqdm(total=queue.qsize(), desc='Checking Difference')
                consumers = [asyncio.create_task(self.mutant_queue_consumer(sqlancer_temp_dir, queue, new_kill, consumer_pbar)) for _ in range(self.max_parallel_tasks)]
                await queue.join()
                consumer_pbar.close()

                for task in consumers:
                    task.cancel()

                await asyncio.gather(*consumers, return_exceptions=True)

            tested_seeds.add(sqlancer_seed)

            print()

            with open(f'{self.output_dir}/fuzzing_test.pkl', 'ab+') as f:
                pickle.dump({'source': self.source_name, 'gen': self.gen, 'cum_kill': new_kill, 'seeds': tested_seeds, 'cum_coverage': in_coverage}, f)
            # print(f"File: {self.source_name}, Covered: {len(in_coverage)}, New Kill: {len(newly_killed)}")


    

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

# output
# a = TestGenerationWorker('alter', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_tracking', '/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_alter_mutations')
# asyncio.run(a.slice_runner(set()))

# killed = set([from previous])
# for log in logs:
#     Run coverage tracking
#     for mutant in covered_mutants:
#         if mutant in killed:
#             continue
        
#         Run differential Test

    


