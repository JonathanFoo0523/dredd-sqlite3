from runner.dredd_test.worker import MutationTestingWorker

from multiprocessing import Pool
import asyncio
import os
import pickle
import argparse
from pathlib import Path
from os.path import isdir, join, isfile


def main():
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Peform mutation testing on dredd-mutated binary.')
    parser.add_argument("dredd_src_path",
                        help="Directory containing dredd binary, and clang tool associated with it.",
                        type=Path)
    parser.add_argument("sqlite_src_path",
                        help="Directory containing sqlite3 source file and test file.",
                        type=Path)
    parser.add_argument("test_files_path",
                        help="Files containing list of test file (eg: test/alter.test\n) to run mutation testing on.",
                        type=Path)
    parser.add_argument("mutation_binary_path",
                        help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    parser.add_argument("output_directory",
                        help="Directory to result of mutation testing",
                        type=Path)
    args = parser.parse_args()

    if not isdir(args.output_directory):
        os.mkdir(args.output_directory)

    # Attempt to load from global regression checkpoint
    source_file_covered = []
    try:
        with open(os.path.join(args.output_directory, 'regression_test.pkl'), 'rb') as f:
            while True:
                obj = pickle.load(f)
                covered = obj['in_coverage_survived'].union(obj['killed'])
                print(f"Source: {obj['source']}; Total: {obj['total']}; Covered: {len(covered)}; Killed: {len(obj['killed'])};")
                source_file_covered.append(obj['source'] + '.c')
    except Exception as err:
        pass
    finally:
        if len(source_file_covered) != 0:
            print("Continuing:")

    # All files that compose sqlite3 can be found in tsrc
    sqlite_c_src_directory = f'{args.sqlite_src_path}/tsrc'
    sqlite_c_src_files = [f for f in os.listdir(sqlite_c_src_directory) if isfile(join(sqlite_c_src_directory, f))]

    excluded_souce_file = [
                            'tclsqlite.c',  # Not Inlcuded in sqlite.c
                            'shell.c',      # Not Inlcuded in sqlite.c
                            'userauth.c',   # Not Inlcuded in sqlite.c
                            'geopoly.c'     # #include-ed onto the end of "rtree.c"
                        ]

    sqlite_c_src_c_files = sorted(list(filter(lambda s: s.split('.')[-1] == 'c' and s not in excluded_souce_file, sqlite_c_src_files) ))

    # Loop through each source file and perform mutation testing
    for file in sqlite_c_src_c_files:
        file = file.split('.')[0]

        with open(args.test_files_path) as test_files:
            tests = [os.path.join(args.sqlite_src_path, line.rstrip('\n')) for line in test_files]

            coverage_bin = os.path.join(args.mutation_binary_path, f'testfixture_{file}_coverage')
            mutation_bin = os.path.join(args.mutation_binary_path, f'testfixture_{file}_mutation')
            mutation_info = os.path.join(args.mutation_binary_path, f'{file}_testfixture_info.json')
            mutant_info_script = os.path.join(args.dredd_src_path, 'scripts', 'query_mutant_info.py')


            asyncio.run(MutationTestingWorker(mutant_info_script, file, coverage_bin, mutation_bin, mutation_info, args.output_directory).async_slice_runner(tests))

if __name__ == '__main__':
    main()


# def main(mutation_binary_dir: str, output_dir: str, dredd_mutant_info_script_path: str):
#     # print(f"Starting multiproceses with {cpu_count()} worker")
#     # pool = Pool(processes=4)
#     # with Pool(8) as pool:
#     #     pool.starmap(worker.run, tqdm(worker_task, total=len(worker_task)))
#     output_dir = f'/home/ubuntu/dredd-sqlite3/sample_output7'
#     source_file_covered = []
#     try:
#         with open(os.path.join(output_dir, 'regression_test.pkl'), 'rb') as f:
#             while True:
#                 obj = pickle.load(f)
#                 covered = obj['in_coverage_survived'].union(obj['killed'])
#                 print(f"Source: {obj['source']}; Total: {obj['total']}; Covered: {len(covered)}; Killed: {len(obj['killed'])};")
#                 source_file_covered.append(obj['source'] + '.c')
#     except Exception as err:
#         pass
#     finally:
#         print("Continuing:")

#     sqlite_c_src_c_files = sorted(list(set(sqlite_c_src_c_files) - set(source_file_covered)))

#     for file in sqlite_c_src_c_files:
#         file = file.split('.')[0]

#         with open('/home/ubuntu/dredd-sqlite3/sample_binary/ss_tests.txt') as test_files:
#             tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_files]
#             # tests = ['/home/ubuntu/sqlite-src/test/tkt3630.test']

#             coverage_bin = os.path.join(mutation_binary_dir, f'testfixture_{file}_coverage')
#             mutation_bin = os.path.join(mutation_binary_dir, f'testfixture_{file}_mutation')
#             mutation_info = os.path.join(mutation_binary_dir, f'{file}_mutation_info.json')

#             asyncio.run(MutationTestingWorker(file, coverage_bin, mutation_bin, mutation_info, output_dir).async_slice_runner(tests))
#     # for i in tqdm(pool.imap(worker, sqlite_c_src_c_files), total=len(sqlite_c_src_c_files), position=0, leave=False):
#     #     pass



