from runner.dredd_test.regression_test import basic_slice_runner
from runner.common.types import TestStatus
from runner.dredd_source.main import sqlite_c_src_c_files
from runner.dredd_test.async_main import async_slice_runner

from runner.dredd_test.async_worker import MutationTestingWorker

from multiprocessing import Pool
from tqdm.auto import tqdm
import asyncio
import os
import pickle


# print(TestStatus.KILLED_FAIL.name)

# with open('/home/ubuntu/dredd-sqlite3/sample_binary/ss_tests.txt') as test_files:
#     tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_files]

# coverage_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_tracking'
# mutation_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_mutations'

# with open('/home/ubuntu/dredd-sqlite3/sample_output/sample_output.csv', 'w') as output_file:
#     with open('/home/ubuntu/dredd-sqlite3/sample_output/sample_killed.txt', 'w') as killed_file:
#         basic_slice_runner(coverage_bin, mutation_bin, tests, output_file, killed_file)

def worker(file: str, output_dir: str):
    file = file.split('.')[0]

    with open('/home/ubuntu/dredd-sqlite3/sample_binary/ss_tests.txt') as test_files:
        tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_files]
        # tests = ['/home/ubuntu/sqlite-src/test/tkt3630.test']

        coverage_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary2/testfixture_{file}_coverage'
        mutation_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary2/testfixture_{file}_mutation'
        mutation_info = f'/home/ubuntu/dredd-sqlite3/sample_binary2/{file}_mutation_info.json'

        # output_dir = f'/home/ubuntu/dredd-sqlite3/sample_output4'
        asyncio.run(MutationTestingWorker(file, coverage_bin, mutation_bin, mutation_info, output_dir).async_slice_runner(tests))


if __name__ == '__main__':
    # print(f"Starting multiproceses with {cpu_count()} worker")
    pool = Pool(processes=4)
    # with Pool(8) as pool:
    #     pool.starmap(worker.run, tqdm(worker_task, total=len(worker_task)))
    output_dir = f'/home/ubuntu/dredd-sqlite3/sample_output5'
    source_file_covered = []
    try:
        with open(os.path.join(output_dir, 'regression_test.pkl'), 'rb') as f:
            while True:
                obj = pickle.load(f)
                covered = obj['in_coverage_survived'].union(obj['killed'])
                print(f"Source: {obj['source']}; Total: {obj['total']}; Covered: {len(covered)}; Killed: {len(obj['killed'])};")
                source_file_covered.append(obj['source'] + '.c')
    except Exception as err:
        pass
    finally:
        print("Continuing:")

    sqlite_c_src_c_files = sorted(list(set(sqlite_c_src_c_files) - set(source_file_covered)))

    for file in sqlite_c_src_c_files:
        worker(file, output_dir)
    # for i in tqdm(pool.imap(worker, sqlite_c_src_c_files), total=len(sqlite_c_src_c_files), position=0, leave=False):
    #     pass