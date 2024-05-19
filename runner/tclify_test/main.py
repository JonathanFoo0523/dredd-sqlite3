# reset_db

# do_execsql_test
# do_catchsql_test
from runner.tclify_test.worker import TCLifyWorker
from pathlib import Path
import argparse
import os
import asyncio
import multiprocessing
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Package test cases into TCL test case.')
    parser.add_argument("mutation_binary_path",
                        help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    parser.add_argument("reduction_output_directory",
                        help="Directory that contains result of result of test case reduction",
                        type=Path)
    parser.add_argument("output_directory",
                    help="Directory to store result of result of test case tcl-ify",
                    type=Path)
    args = parser.parse_args()

    if not os.path.isdir(args.output_directory):
        os.mkdir(args.output_directory)

    async_worker = TCLifyWorker(args.mutation_binary_path, args.reduction_output_directory, args.output_directory)

    tasks = os.listdir(args.reduction_output_directory)
    with multiprocessing.Pool() as p:
        list(tqdm(p.imap(async_worker.mpwrap_runner, tasks), total=len(tasks)))
    # asyncio.run(async_worker.runner('alter'))

if __name__ == "__main__":
    main()