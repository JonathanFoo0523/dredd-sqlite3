from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST
from runner.common.types import MutantID, TestStatus
from runner.common.async_utils import subprocess_run

import time
import tempfile
import os
import asyncio
import re
import pickle

DREDD_MUTANT_INFO_SCRIPT='/home/ubuntu/dredd/scripts/query_mutant_info.py'

class Stats:
    def __init__(self, total_mutants):
        self.total_mutants = total_mutants
        self.killed_mutants = set()
        self.skipped_mutants = set()
        self.survived_mutants = set()

    def add_killed(self, mutant):
        self.killed_mutants.add(mutant)
    
    def add_survived(self, mutant):
        self.survived_mutants.add(mutant)

    def add_skipper(self, mutant):
        self.killed_mutants.add(mutant)

    def get_killed_count(self):
        return len(self.killed_mutants)

    def get_skipped_count(self):
        return len(self.skipped_mutants)

    def get_survived_count(self):
        return len(self.survived_mutants)

    def get_total_count(self):
        return len(self.killed_mutants) + len(self.skipped_mutants) + len(self.survived_mutants)

    def checked_all_mutants(self) -> bool:
        # print(self.get_total_count(), self.total_mutants)
        return self.get_total_count() == self.total_mutants

# Performing Mutation Testing on One source file
class MutationTestingWorker:
    def __init__(self, source_name: str, tracking_binary: str, mutation_binary: str, mutation_info: str, output_dir: str, max_parallel_tasks: int = 16):
        self.source_name = source_name
        self.max_parallel_tasks = max_parallel_tasks
        self.tracking_binary = tracking_binary
        self.mutation_binary = mutation_binary
        self.mutation_info = mutation_info

        assert os.path.isdir(output_dir)
        self.output_dir = output_dir
        if not os.path.isdir(output_dir):
            os.mkdir(os.path.join(output_dir, source_name))


    async def get_largest_mutant_id(self) -> set[MutantID]:
        stdout, _, _ = await subprocess_run(['python3', DREDD_MUTANT_INFO_SCRIPT, self.mutation_info, '--largest-mutant-id'], stdout=asyncio.subprocess.PIPE)

        return int(stdout)


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


    async def run_testfixture(self, test_path: str, mutant: MutantID = None, timeout: float = None) -> (TestStatus, str):
        env_copy = os.environ.copy()
        if mutant is not None:
            env_copy["DREDD_ENABLED_MUTATION"] = str(mutant)
        
        with tempfile.TemporaryDirectory() as temp_test_dir:
            stdout, stderr, returncode = await subprocess_run([self.mutation_binary, test_path], timeout=timeout, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env_copy, cwd=temp_test_dir)

        if returncode == -1:
            # Timeout (finger cross)
            return (TestStatus.KILLED_TIMEOUT, stderr.decode().rstrip('/n'))
        elif returncode == 1:
            # Fail a test
            output = ''.join(stdout.decode())
            match = re.search('(\d)+ errors out of (\d)+', output)
            description = match.group() if match is not None else ""
            return (TestStatus.KILLED_FAILED, description)
        elif returncode == 0:
            # Pass all test
            output = ''.join(stdout.decode())
            match = re.search('(\d)+ errors out of (\d)+', output)
            description = match.group() if match is not None else ""
            return (TestStatus.SURVIVED, description)
        else:
            return (TestStatus.KILLED_CRASHED, f"died with code {returncode}")


    async def mutation_test_task(self, queue, killed_set, stat, test, timeout):
        while True:
            mutant = await queue.get()

            if mutant in killed_set:
                stat.add_skipper(mutant)
            else:
                status, description = await self.run_testfixture(test, mutant=mutant, timeout=timeout)
                if status == TestStatus.SURVIVED:
                    stat.add_survived(mutant)
                else:
                    stat.add_killed(mutant)
                    with open(f'{self.output_dir}/{self.source_name}/killed.txt', 'a+') as killedfile:
                        killedfile.write(f"{mutant}\n")
                    killed_set.add(mutant)

                with open(f'{self.output_dir}/output.csv', 'a+') as outputfile:
                    outputfile.write(f"{status.name}, {test[24:]}, {mutant}, {description}\n")

            print(f"Killed: {stat.get_killed_count()}, Survived: {stat.get_survived_count()}, Skipped: {stat.get_skipped_count()}", end='\n' if stat.checked_all_mutants() else '\r')
            queue.task_done()


    async def async_slice_runner(self, testset: list[str]):
        with open(f'{self.output_dir}/{self.source_name}/output.csv', 'a+') as outputfile:
            outputfile.write(f"status, test_name, mutant_id, description\n")

        killed = set()
        in_coverage = set()
        largest_mutants = await self.get_largest_mutant_id()

        for index, test in enumerate(testset):
            print("Running:", test, f"{index + 1}/{len(testset)}")

            start = time.time()
            mutants = await self.get_mutations_in_coverage_by_test(test)
            end = time.time()
            base_time = end - start
            print(f"Time: {base_time}s")
            in_coverage.update(mutants)

            print("Number of mutants in coverage", len(mutants))

            if len(mutants) == 0:
                print()
                continue        

            queue = asyncio.Queue()
            stats = Stats(len(mutants))

            for mutant in mutants:
                queue.put_nowait(mutant)

            tasks = []
            for i in range(min(self.max_parallel_tasks, len(mutants))):
                task = asyncio.create_task(self.mutation_test_task(queue, killed, stats, test, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST))
                tasks.append(task)

            await queue.join()

            for task in tasks:
                task.cancel()

            await asyncio.gather(*tasks, return_exceptions=True)
            with open(f'{self.output_dir}/{self.source_name}/picklefile', 'ab+') as f:
                # print({'test_dir':test, 'in_coverage': mutants, 'time': base_time, 'killed': stats.killed_mutants, 'survived': stats.survived_mutants, 'skipped':  stats.skipped_mutants})
                pickle.dump({'test_file':test, 'in_coverage': mutants, 'time': base_time, 'killed': stats.killed_mutants, 'survived': stats.survived_mutants, 'skipped':  stats.skipped_mutants}, f)
            print()
            # print(dict(killed=killed, last_test=test))
        with open(f'{self.output_dir}/picklefile', 'ab+') as f:
            pickle.dumps({file: {'total': largest_mutants, 'killed': killed, 'in_coverage_survived': in_coverage - killed,  'not_in_coverage': largest_mutants - in_coverage}})

    
