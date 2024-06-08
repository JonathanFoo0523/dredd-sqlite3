from runner.common.types import MutantID
from runner.generate_test.worker import TestGenerationWorker

import time
from multiprocessing import Pool, cpu_count
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
                # print(">>>", obj['source'], len(obj['killed']), obj['total'])
                covered_file_kill_pair.append((obj['source'], obj['killed'], obj['total']))
    except EOFError:
        # Ran out of input
        pass

    return covered_file_kill_pair


def main():
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Generate test cases.')
    parser.add_argument('--oracle', nargs='?', const="FUZZER", type=str)
    parser.add_argument("sqlancer_jar_path",
                        help="Path to SQLancer JAR file.",
                        type=Path)
    parser.add_argument("mutation_binary_path",
                        help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    parser.add_argument("regression_output_directory",
                        help="Directory which contains result of regression/mutation testing.",
                        type=Path)
    parser.add_argument("output_directory",
                        help="Directory to store result of result of fuzz testing and interesting test cases",
                        type=Path)
    args = parser.parse_args()

    if args.oracle is None:
        args.oracle = "FUZZER"
    if args.oracle in ['NoREC', 'AGGREGATE', 'WHERE', 'DISTINCT', 'GROUP_BY', 'HAVING', 'QUERY_PARTITIONING']:
        enable_qpg = True
    else:
        enable_qpg = False
    
    if not os.path.isdir(args.output_directory):
        os.mkdir(args.output_directory)

    covered = get_regression_tested_file(args.regression_output_directory)

    # Attempt to load from global fuzzing checkpoint
    source_file_covered = dict()
    try:
        with open(os.path.join(args.output_directory, 'fuzzing_test.pkl'), 'rb') as f:
            while True:
                obj = pickle.load(f)
                # covered = obj['in_coverage_survived'].union(obj['killed'])
                print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")
                # source_file_covered.append(obj['source'])
                if obj['source'] in source_file_covered:
                    source_file_covered[obj['source']] += 1
                else:
                    source_file_covered[obj['source']] = 1
    except EOFError as err:
        pass
    except FileNotFoundError:
        pass
    finally:
        if len(source_file_covered) != 0:
            print("Continuing:")


    for file, killed, total in covered:
        if file in source_file_covered and source_file_covered[file] == 8:
            continue

        if total == 0:
            print(f"Skip {file} with 0 mutants")
            continue

        if file == 'build':
            continue

        # print(">>>>", file, len(killed))

        coverage_bin = os.path.join(args.mutation_binary_path, f'sqlite3_{file}_coverage')
        mutation_bin = os.path.join(args.mutation_binary_path, f'sqlite3_{file}_mutation')
        async_worker = TestGenerationWorker(args.sqlancer_jar_path, file, killed, coverage_bin ,mutation_bin, args.output_directory, max_parallel_tasks=cpu_count(), total_gen=8, oracle=args.oracle, enable_qpg=enable_qpg)
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
