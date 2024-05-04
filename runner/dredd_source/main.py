from runner.dredd_source.worker import DreddAndCompileWorker
import time
from random import randint
from multiprocessing import Pool, cpu_count
from runner.common.istarmap import istarmap
from tqdm.auto import tqdm
import sys

from os import listdir
from os.path import isfile, join

SQLITE_SRC_CHECKOUT='/home/ubuntu/sqlite-src-cp'
DREDD_EXECUTABLE='/home/ubuntu/dredd/third_party/clang+llvm/bin/dredd'

sqlite_c_src_directory = f'{SQLITE_SRC_CHECKOUT}/tsrc'
sqlite_c_src_files = [f for f in listdir(sqlite_c_src_directory) if isfile(join(sqlite_c_src_directory, f))]

excluded = [
            'tclsqlite.c',  # Not Inlcuded in sqlite.c
            'shell.c',      # Not Inlcuded in sqlite.c
            'userauth.c',   # Not Inlcuded in sqlite.c
            'geopoly.c'     # #include-ed onto the end of "rtree.c"
            ]

sqlite_c_src_c_files = list(filter(lambda s: s.split('.')[-1] == 'c' and s not in excluded, sqlite_c_src_files) )
targets = ['testfixture', 'sqlite3']

worker_task = [(file, target) for file in sqlite_c_src_c_files for target in targets]

# print(list(sqlite_c_src_c_files))
# exit(0)

# def task_wrapper(file: str):
#     try:
#         worker = DreddAndCompileWorker(SQLITE_SRC_CHECKOUT, '/home/ubuntu/dredd-sqlite3/sample_binary2')
#         worker.run(file)
#     except Exception as err:
#         print(f"{file} FAILED WITH ERROR")
#         print(err)

worker = DreddAndCompileWorker(SQLITE_SRC_CHECKOUT, '/home/ubuntu/dredd-sqlite3/sample_binary')

# sqlite_c_src_c_files=[('main.c', 'testfixture'), ('main.c', 'sqlite3')]
if __name__ == '__main__':
    # print(f"Starting multiproceses with {cpu_count()} worker")
    pool = Pool(processes=4)
    # with Pool(8) as pool:
    #     pool.starmap(worker.run, tqdm(worker_task, total=len(worker_task)))
    for i in tqdm(pool.istarmap(worker.run, worker_task), total=len(worker_task), position=0, leave=False):
        pass


# Error while processing /tmp/tmpnbmv4t1z/tsrc/geopoly.c.
