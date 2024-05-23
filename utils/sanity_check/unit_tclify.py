import argparse
from pathlib import Path
import sys
import os 
import multiprocessing
from tqdm import tqdm
import re

sys.path.append('/home/ubuntu/dredd-sqlite3')
from runner.tclify_test.worker import TCLifyWorker

class UnitTCLifyWorker(TCLifyWorker):
    # def __init__(self, mutation_dir, reduction_dir, output_dir):
    #     super(mutation_dir, reduction_dir, output_dir)

    async def runner(self, source):
        testcase_mutants_dict = dict()
        for file in os.listdir(os.path.join(self.reduction_dir, source)):
            abs_file_path = os.path.abspath(os.path.join(self.reduction_dir, source, file))
            hash = self.get_file_hash(abs_file_path)
            mutant = re.search(r'testcase_(\d+).log', file).group(1)
            if hash in testcase_mutants_dict:
                testcase_mutants_dict[hash].append(mutant)
            else:
                testcase_mutants_dict[hash] = [mutant]

        for j, mutants in enumerate(testcase_mutants_dict.values()):
            with open(os.path.join(self.output_dir, f'{source}_{j}.test'), 'w+') as f:
                f.write('set testdir [file dirname $argv0]\n')
                f.write('source $testdir/tester.tcl\n\n')
            
                file_path = os.path.join(self.reduction_dir, source, f'testcase_{mutants[0]}.log')
                try:
                    groups = await self.group_sql(file_path, source)
                except Exception as err:
                    print(err, source, mutants[0])
                    return
                f.write(f'# kill mutants {sorted(mutants)}\n')
                f.write('reset_db\n')
                f.write('sqlite3_db_config db DEFENSIVE 1\n')
                # f.write('fconfigure db -encoding binary -translation binary\n')
               
                # check if sqls contain load_extension()
                for sqls, _ in groups:
                    if 'load_extension' in ''.join(sqls):
                        f.write('sqlite3_enable_load_extension db 1\n')
                        break
                

                for i, (sqls, (stdout, stderr)) in enumerate(groups):
                    if stderr is not None:
                        f.write(f'do_catchsql_test {source}-dredd-{j+1}.{i+1}' + ' {\n')
                        f.write('  ')
                        f.write('  '.join(sqls))
                        f.write('} {1 {' + stderr + '}}\n')
                    else:
                        f.write(f'do_execsql_test {source}-dredd-{j+1}.{i+1}' + ' {\n')
                        f.write('  ')
                        f.write('  '.join(sqls))
                        f.write('} {' + (stdout if stdout else "") + '}\n')

                f.write('\n')
                f.write('finish_test\n')




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

    async_worker = UnitTCLifyWorker(args.mutation_binary_path, args.reduction_output_directory, args.output_directory)

    tasks = os.listdir(args.reduction_output_directory)
    with multiprocessing.Pool() as p:
        list(tqdm(p.imap(async_worker.mpwrap_runner, tasks), total=len(tasks)))

if __name__ == "__main__":
    main()
