from runner.common.types import MutantID
from runner.generate_test.worker import TestGenerationWorker

import time
from multiprocessing import Pool
from tqdm import tqdm
import os
import pickle
import asyncio


def get_regression_tested_file(output_dir: str):
    covered_file_kill_pair = []
    try:
        with open(os.path.join(output_dir, 'regression_test.pkl'), 'rb') as f:
            while True:
                obj = pickle.load(f)
                covered_file_kill_pair.append((obj['source'], obj['killed']))
    except EOFError:
        # Ran out of input
        pass

    return covered_file_kill_pair

def worker(file: str, killed: set[MutantID], output_dir: str):
    coverage_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_{file}_coverage'
    mutation_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_{file}_mutation'
    async_worker = TestGenerationWorker(file, killed, coverage_bin ,mutation_bin, output_dir)
    asyncio.run(async_worker.slice_runner())


if __name__ == '__main__':
    output_dir = f'/home/ubuntu/dredd-sqlite3/sample_output5'
    covered = get_regression_tested_file(output_dir)
    for file, killed in covered:
        print(len(killed))
        worker(file, killed, output_dir)
