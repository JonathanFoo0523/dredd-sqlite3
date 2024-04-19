from runner.common.async_utils import subprocess_run
import asyncio
import tempfile
import os

import subprocess
import re
import time

from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST
from runner.common.types import MutantID, TestStatus


async def get_mutations_in_coverage_by_test(tracking_binary: str, test_path: str) -> set[MutantID]:
    with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-dredd-test') as temp_coverage_file:
        coverage_filepath = temp_coverage_file.name
        env_copy = os.environ.copy()
        env_copy["DREDD_MUTANT_TRACKING_FILE"] = coverage_filepath

        try:
            with tempfile.TemporaryDirectory() as temp_test_dir:
                await subprocess_run([tracking_binary, test_path], env=env_copy, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, cwd=temp_test_dir)
        except Exception as err:
            print(err)
            exit(1)

        temp_coverage_file.seek(0)
        covered_mutants = [int(line.rstrip()) for line in temp_coverage_file]

    return covered_mutants

async def run_testfixture(testfixture_binary: str, test_path: str, mutant: MutantID = None, timeout: float = None) -> (TestStatus, str):
    env_copy = os.environ.copy()
    if mutant is not None:
        env_copy["DREDD_ENABLED_MUTATION"] = str(mutant)
    
    with tempfile.TemporaryDirectory() as temp_test_dir:
        stdout, stderr, returncode = await subprocess_run([testfixture_binary, test_path], timeout=timeout, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env_copy, cwd=temp_test_dir)

    # print(stdout.decode().split('\n'), stderr.decode().split('\n'), returncode)

    if returncode == -1:
        # Timeout (finger cross)
        return (TestStatus.KILLED_TIMEOUT, stderr.decode().rstrip('/n'))
    elif returncode == 1:
        # Fail a test
        output = ''.join(stdout.decode())
        match = re.search('(\d)+ errors out of (\d)+', output)
        description = match.group() if match is not None else ""
        return (TestStatus.KILLED_FAIL, description)
    elif returncode == 0:
        # Pass all test
        output = ''.join(stdout.decode())
        match = re.search('(\d)+ errors out of (\d)+', output)
        description = match.group() if match is not None else ""
        return (TestStatus.SURVIVED, description)
    else:
        return (TestStatus.KILLED_FAIL, f"died with code {returncode}")

class Stats:
    def __init__(self):
        self.killCount = 0
        self.surviveCount = 0
        self.skipCount = 0
        self.totalCount = 0

    def inc_kill(self):
        self.killCount += 1
        self.totalCount += 1
    
    def inc_survive(self):
        self.surviveCount += 1
        self.totalCount += 1

    def inc_skip(self):
        self.skipCount += 1
        self.totalCount += 1


async def worker(queue, killed_set, killedfile, outputfile, mutation_binary, stat, test, timeout, mutants_len):
    while True:
        mutant = await queue.get()

        if mutant in killed_set:
            stat.inc_skip()
        else:
            status, description = await run_testfixture(mutation_binary, test, mutant=mutant, timeout=timeout)
            if status == TestStatus.SURVIVED:
                stat.inc_survive()
            else:
                stat.inc_kill()
                killedfile.write(f"{mutant}\n")
                killed_set.add(mutant)

            outputfile.write(f"{status.name}, {test[24:]}, {mutant}, {description}\n")

        print(f"Killed: {stat.killCount}, Survived: {stat.surviveCount}, Skipped: {stat.skipCount}", end='\r' if mutants_len != stat.totalCount else '\n')

        # Notify the queue that the "work item" has been processed.
        queue.task_done()

        

async def async_slice_runner(coverage_binary: str, mutation_binary: str, testset: list[str], outputfile, killedfile):
    outputfile.write(f"status, test_name, mutant_id, description\n")
    killed = set()

    for index, test in enumerate(testset):
        print("Running:", test, f"{index + 1}/{len(testset)}")

        start = time.time()
        mutants = await get_mutations_in_coverage_by_test(coverage_binary, test)
        end = time.time()
        base_time = end - start
        print(f"Time: {base_time}s")

        print("Number of mutants in coverage", len(mutants))

        if len(mutants) == 0:
            print()
            continue        

        queue = asyncio.Queue()
        stats = Stats()

        for mutant in mutants:
            queue.put_nowait(mutant)

        tasks = []
        for i in range(min(16, len(mutants))):
            task = asyncio.create_task(worker(queue, killed, killedfile, outputfile, mutation_binary, stats, test, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST, mutants_len=len(mutants)))
            tasks.append(task)

        await queue.join()

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        print()


with open('/home/ubuntu/dredd-sqlite3/sample_binary/ss_tests.txt') as test_files:
    tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_files]
    # tests = ['/home/ubuntu/sqlite-src/test/tkt3630.test']

    coverage_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_tracking'
    mutation_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_mutations'

    with open('/home/ubuntu/dredd-sqlite3/sample_output2/sample_output.csv', 'w') as output_file:
        with open('/home/ubuntu/dredd-sqlite3/sample_output2/sample_killed.txt', 'w') as killed_file:
            asyncio.run(async_slice_runner(coverage_bin, mutation_bin, tests, output_file, killed_file))