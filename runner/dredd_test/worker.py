from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST, MINIMUM_REGRESSION_TEST_TIMEOUT_SECONDS
from runner.common.types import MutantID, TestStatus
from runner.common.async_utils import subprocess_run, TIMEOUT_RETCODE
from runner.common.counter import Stats

import time
import tempfile
import os
import asyncio
import re
import pickle
import json
import ndjson
from tqdm import tqdm

# DREDD_MUTANT_INFO_SCRIPT='/home/ubuntu/dredd/scripts/query_mutant_info.py'


# Performing Mutation Testing on one source file
class MutationTestingWorker:
    def __init__(self, dredd_mutant_info_script_path, source_name: str, tracking_binary: str, mutation_binary: str, mutation_info: str, output_dir: str, max_parallel_tasks: int = 4):
        assert(os.path.isfile(dredd_mutant_info_script_path))
        assert(os.path.isfile(tracking_binary))
        assert(os.path.isfile(mutation_binary))
        assert(os.path.isfile(mutation_info))

        self.dredd_mutant_info_script_path = dredd_mutant_info_script_path
        self.source_name = source_name
        self.tracking_binary = tracking_binary
        self.mutation_binary = mutation_binary
        self.mutation_info = mutation_info
        self.max_parallel_tasks = max_parallel_tasks

        assert os.path.isdir(output_dir)
        self.output_dir = output_dir
        if not os.path.isdir(os.path.join(output_dir, source_name)):
            os.mkdir(os.path.join(output_dir, source_name))

        self.outputfile = os.path.join(output_dir, source_name, 'output.csv')
        self.killedfile = os.path.join(output_dir, source_name, 'killed.txt')
        self.coverage_checkpoint = os.path.join(output_dir, source_name, 'coverage_checkpoint.json')
        self.regression_checkpoint = os.path.join(output_dir, source_name, 'regression_checkpoint.json')



    async def get_total_mutants(self) -> int:
        stdout, stderr, code = await subprocess_run(['python3', self.dredd_mutant_info_script_path, self.mutation_info, '--largest-mutant-id'], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    
        if code:    #  TO FIX: dredd script crashed when no mutation is possible
            return 0        

        return int(stdout) + 1


    async def get_mutations_in_coverage_by_test(self, test_path: str) -> set[MutantID]:
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-dredd-test') as temp_coverage_file:
            coverage_filepath = temp_coverage_file.name
            env_copy = os.environ.copy()
            env_copy["DREDD_MUTANT_TRACKING_FILE"] = coverage_filepath

            try:
                with tempfile.TemporaryDirectory() as temp_test_dir:
                    await subprocess_run([self.tracking_binary, test_path], env=env_copy, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, cwd=temp_test_dir)
            except Exception as err:
                print(err)
                exit(1)

            temp_coverage_file.seek(0)
            covered_mutants = sorted([int(line.rstrip()) for line in temp_coverage_file])

        return set(covered_mutants)


    async def run_testfixture(self, test_path: str, mutant: MutantID = None, timeout: float = None) -> tuple[TestStatus, str]:
        env_copy = os.environ.copy()
        if mutant is not None:
            env_copy["DREDD_ENABLED_MUTATION"] = str(mutant)
        
        with tempfile.TemporaryDirectory() as temp_test_dir:
            stdout, stderr, returncode = await subprocess_run([self.mutation_binary, test_path], timeout=timeout, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env_copy, cwd=temp_test_dir)

        if returncode == TIMEOUT_RETCODE:
            # Timeout (Might be a problem when child process could have the same return code)
            return (TestStatus.KILLED_TIMEOUT, stderr.decode().rstrip('/n'))
        elif returncode == 1:
            # Fail a test
            try:
                output = ''.join(stdout.decode())
                match = re.search('(\d)+ errors out of (\d)+', output)
                description = match.group() if match is not None else ""
                return (TestStatus.KILLED_FAILED, description)
            except:
                return (TestStatus.KILLED_FAILED, "FAILED TO READ OUTPUT")
        elif returncode == 0:
            # Pass all test
            output = ''.join(stdout.decode())
            match = re.search('(\d)+ errors out of (\d)+', output)
            description = match.group() if match is not None else ""
            return (TestStatus.SURVIVED, description)
        else:
            return (TestStatus.KILLED_CRASHED, f"died with code {returncode}")


    def load_progress(self) -> tuple[asyncio.Queue, set[MutantID], set[MutantID], set[str], int]:
        # queue, killed, in_coverage, coverage_checked_test, queue_length
        queue = asyncio.Queue()
        killed = set()
        in_coverage = set()
        queue_length = 0

        # dict(test, (set[MutantID], time))
        test_to_check = dict()

        if os.path.isfile(self.coverage_checkpoint):
            with open(self.coverage_checkpoint, 'r') as f:
                try:
                    objs = ndjson.load(f)
                    for obj in objs:
                        test_to_check[obj['test']] = (obj['in_coverage'], obj['time'])
                        in_coverage.update(obj['in_coverage'])
                        queue_length += len(obj['in_coverage'])
                except Exception as err:
                    print(err)
                    pass

        if os.path.isfile(self.regression_checkpoint):
            with open(self.regression_checkpoint, 'r') as f:
                try:
                    objs = ndjson.load(f)
                    for obj in objs:
                        # test, mutant, status
                        if obj['status'] != TestStatus.SURVIVED.name:
                            killed.add(obj['mutant'])
                        test_to_check[obj['test']][0].remove(obj['mutant'])
                except Exception as err:
                    print(err)
                    pass

        for test, (survived_mutants, base_time) in test_to_check.items():
            for mutant in survived_mutants:
                queue.put_nowait((test, base_time, mutant))


        return queue, killed, in_coverage, set(test_to_check.keys()), queue_length



    async def mutant_queue_producer(self, queue: asyncio.Queue, killed: set[MutantID], in_coverage: set[MutantID], tests: list[str], pbar=None):
        for test in tests:
            
            start = time.time()
            try:
                mutants = await self.get_mutations_in_coverage_by_test(test)
            except Exception as err:
                print(err)
            end = time.time()
            base_time = end - start
            in_coverage.update(mutants)
            for mutant in mutants:
                if mutant in killed:
                    continue
                queue.put_nowait((test, base_time, mutant))

            # print(mutants)
            with open(self.coverage_checkpoint, 'a+') as f:
                json.dump({'test': test, 'in_coverage': list(mutants), 'time': base_time}, f)
                f.write('\n')

            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Covered': len(in_coverage)})


    async def mutant_queue_consumer(self, queue: asyncio.Queue, killed: set[MutantID], pbar=None):
        while True:            
            test, base_time, mutant = await queue.get()

            if mutant not in killed:
                timeout = max(base_time * TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST, MINIMUM_REGRESSION_TEST_TIMEOUT_SECONDS)
                status, description = await self.run_testfixture(test, mutant=mutant, timeout=timeout)
                if status != TestStatus.SURVIVED:
                    with open(self.killedfile, 'a+') as killedfile:
                        killedfile.write(f"{mutant}\n")
                    killed.add(mutant)

                with open(self.outputfile, 'a+') as outputfile:
                    outputfile.write(f"{status.name}, {test[24:]}, {mutant}, {description}\n")

                with open(self.regression_checkpoint, 'a+') as f:
                    json.dump({'test': test, 'mutant': mutant, 'status': status.name, 'description': description}, f) 
                    f.write('\n')
            else:
                with open(self.regression_checkpoint, 'a+') as f:
                    json.dump({'test': test, 'mutant': mutant, 'status': 'SKIPPED'}, f) 
                    f.write('\n')

            queue.task_done()

            if pbar:
                pbar.update(1)
                pbar.set_postfix({'Killed': len(killed)})


    
    async def async_slice_runner(self, testset: list[str]):

        print()
        print("Running regression test:", self.source_name)

        self.total_mutants = await self.get_total_mutants()
        print("Total Mutants", self.total_mutants)

        queue, killed, in_coverage, coverage_checked_test, queue_length = self.load_progress()


        if not os.path.isfile(self.outputfile):
            with open(self.outputfile, 'w+') as f:
                f.write(f"status, test_name, mutant_id, description\n")

        
        producers_pbar = tqdm(total=len(testset), desc='Finding coverage')
        testset = [test for test in testset if test not in coverage_checked_test]
        producers_pbar.update(n=len(coverage_checked_test))
        producers_pbar.refresh()
        producers = [asyncio.create_task(self.mutant_queue_producer(queue, killed, in_coverage, testset[i :: self.max_parallel_tasks], producers_pbar)) for i in range(self.max_parallel_tasks)]
        await asyncio.gather(*producers, return_exceptions=True)
        producers_pbar.close()
        
        consumer_pbar = tqdm(total=max(queue.qsize(), queue_length), desc='Running unittest')
        consumer_pbar.update(n=max(queue_length - queue.qsize(), 0))
        consumer_pbar.refresh()

        consumers = [asyncio.create_task(self.mutant_queue_consumer(queue, killed, consumer_pbar)) for _ in range(self.max_parallel_tasks)]
        await queue.join()
        consumer_pbar.close()

        for task in consumers:
            task.cancel()

        await asyncio.gather(*consumers, return_exceptions=True)

        with open(f'{self.output_dir}/regression_test.pkl', 'ab+') as f:
            pickle.dump({'source': self.source_name, 'total': self.total_mutants, 'killed': killed, 'in_coverage_survived': in_coverage - killed,  'not_in_coverage': set(m for m in range(self.total_mutants)) - in_coverage}, f)

    
