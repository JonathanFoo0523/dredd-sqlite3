from runner.common.types import MutantID
from runner.generate_test.worker import TestGenerationWorker

import time
from multiprocessing import Pool
from tqdm import tqdm
import os
import pickle
import asyncio
import argparse
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Generate test cases.')
    parser.add_argument("sqlancer_jar_path",
                        help="Path to SQLancer JAR file.",
                        type=Path)
    parser.add_argument("mutation_binary_path",
                        help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    parser.add_argument("output_directory",
                        help="Directory to result of mutation testing",
                        type=Path)
    args = parser.parse_args()
    
    assert os.isdir(args.output_directory)

    covered = get_regression_tested_file(output_dir)

    # Attempt to load from global fuzzing checkpoint
    source_file_covered = []
    try:
        with open(os.path.join(output_dir, 'fuzzing_test.pkl'), 'rb') as f:
            while True:
                obj = pickle.load(f)
                # covered = obj['in_coverage_survived'].union(obj['killed'])
                print(f"Source: {obj['source']}; New Kill: {len(obj['new kill'])}; Covered: {len(obj['coverage'])};")
                source_file_covered.append(obj['source'])
    except Exception as err:
        pass
    finally:
        if len(source_file_covered) != 0:
            print("Continuing:")


    for file, killed in covered:
        if file in source_file_covered:
            continue

        coverage_bin = os.path.join(args.mutation_binary_path, f'sqlite3_{file}_coverage')
        mutation_bin = os.path.join(args.mutation_binary_path, f'sqlite3_{file}_mutation')
        async_worker = TestGenerationWorker(args.sqlancer_jar_path, file, killed, coverage_bin ,mutation_bin, output_dir)
        asyncio.run(async_worker.slice_runner())


# def worker(file: str, killed: set[MutantID], output_dir: str):
#     coverage_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_{file}_coverage'
#     mutation_bin = f'/home/ubuntu/dredd-sqlite3/sample_binary/sqlite3_{file}_mutation'
#     async_worker = TestGenerationWorker(file, killed, coverage_bin ,mutation_bin, output_dir)
#     asyncio.run(async_worker.slice_runner())


if __name__ == '__main__':
    main()
    # output_dir = f'/home/ubuntu/dredd-sqlite3/sample_output5'
    # covered = get_regression_tested_file(output_dir)
    # for file, killed in covered:
    #     print(len(killed))
    #     worker(file, killed, output_dir)
