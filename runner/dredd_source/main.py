from runner.dredd_source.worker import DreddAndCompileWorker
import argparse
from pathlib import Path

from os import listdir, mkdir
from os.path import isfile, join, isdir
from tqdm import tqdm

# SQLITE_SRC_CHECKOUT='/home/ubuntu/sqlite-src-cp'
# DREDD_EXECUTABLE='/home/ubuntu/dredd/third_party/clang+llvm/bin/dredd'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dredd_src_path",
                        help="Directory containing dredd binary, and clang tool associated with it.",
                        type=Path)
    parser.add_argument("sqlite_src_path",
                        help="Directory containing sqlite3 source file and test file",
                        type=Path)
    parser.add_argument("output_directory",
                        help="Directory to score binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    args = parser.parse_args()

    if isdir(args.output_directory):
        print(f"Replacing content in {args.output_directory}")
    else:
        mkdir(args.output_directory)

    # All files that compose sqlite3 can be found in tsrc
    sqlite_c_src_directory = f'{args.sqlite_src_path}/tsrc'
    sqlite_c_src_files = [f for f in listdir(sqlite_c_src_directory) if isfile(join(sqlite_c_src_directory, f))]

    excluded_souce_file = [
                            'tclsqlite.c',  # Not Inlcuded in sqlite.c
                            'shell.c',      # Not Inlcuded in sqlite.c
                            'userauth.c',   # Not Inlcuded in sqlite.c
                            'geopoly.c'     # #include-ed onto the end of "rtree.c"
                        ]

    sqlite_c_src_c_files = list(filter(lambda s: s.split('.')[-1] == 'c' and s not in excluded_souce_file, sqlite_c_src_files) )

    # Binary to compile
    targets = ['testfixture', 'sqlite3']

    worker_task = [(file, target) for file in sqlite_c_src_c_files for target in targets]
    worker = DreddAndCompileWorker(args.dredd_src_path, args.sqlite_src_path, args.output_directory)

    # dredd and compile
    for file, target in tqdm(worker_task):
        worker.run(file, target)

if __name__ == "__main__":
    main()



# worker = DreddAndCompileWorker(SQLITE_SRC_CHECKOUT, '/home/ubuntu/dredd-sqlite3/sample_binary')

# # sqlite_c_src_c_files=[('main.c', 'testfixture'), ('main.c', 'sqlite3')]
# if __name__ == '__main__':
#     # print(f"Starting multiproceses with {cpu_count()} worker")
#     pool = Pool(processes=4)
#     # with Pool(8) as pool:
#     #     pool.starmap(worker.run, tqdm(worker_task, total=len(worker_task)))
#     for i in tqdm(pool.istarmap(worker.run, worker_task), total=len(worker_task), position=0, leave=False):
#         pass

