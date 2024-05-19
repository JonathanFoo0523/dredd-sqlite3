from runner.reduce_test.worker import TestReductionWorker

import argparse
import shutil
from pathlib import Path
import asyncio
import os

def main():
    assert shutil.which('creduce') is not None, "creduce not found"
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Reduce test cases.')
    parser.add_argument("mutation_binary_path",
                        help="Directory containing binary of mutated file, binary of mutant coverage, and mutant info file",
                        type=Path)
    parser.add_argument("generation_output_directory",
                        help="Directory which contains result of regression/mutation testing.",
                        type=Path)
    parser.add_argument("output_directory",
                        help="Directory to store result of result of test case reduction",
                        type=Path)
    args = parser.parse_args()

    if not os.path.isdir(args.output_directory):
        os.mkdir(args.output_directory)


    async_worker = TestReductionWorker(args.mutation_binary_path, args.generation_output_directory, args.output_directory)
    asyncio.run(async_worker.runner())

    return 1


if __name__ == "__main__":
    main()