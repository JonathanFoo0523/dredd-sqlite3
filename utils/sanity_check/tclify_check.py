import subprocess
import os
import argparse
import tempfile
import re
import shutil
import pickle


def parse_tests(filename):
    kill_pattern = re.compile(r"# kill mutants \['(\d+)',?.*?\]")

    test_end_pattern = re.compile(r"finish_test")

    tests = []
    current_mutants = []
    test_block = ""
    recording = False

    with open(filename, 'r') as file:
        for line in file:
            if kill_pattern.search(line):
                if recording:
                    tests.append((current_mutants, test_block.strip()))
                current_mutants = [int(s) for s in re.findall(r"'(\d+)'", line)]
                recording = True
                test_block = ""
            elif test_end_pattern.search(line) and recording:
                pass
            elif recording:
                test_block += line

        if recording:
            tests.append((current_mutants, test_block.strip()))

    return tests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dredd_output_directory")
    parser.add_argument("tclify_output_directory")
    args = parser.parse_args()
    total_no_of_unit_test = total_commented_out = total_total_mutants = total_succ_mutant = total_crash_mutant = total_pass_mutant = 0

    for source in sorted(os.listdir(args.tclify_output_directory)):
        source, ext = source.split('.')
        if ext != 'test':
            continue

        # if source != 'alter':
            # continue
        # print(source)
        textfixture_bin = os.path.abspath(os.path.join(args.dredd_output_directory, f'testfixture_{source}_mutation'))
        tcl_test = os.path.abspath(os.path.join(args.tclify_output_directory, f'{source}.test'))
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.run([textfixture_bin, tcl_test, '--verbose=0'], cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        test_result = re.search(r'(\d+) errors out of (\d+) .*', proc.stdout.decode())


        no_of_failed_test = -1
        try:
            no_of_unit_test = int(test_result.group(2)) - 1
            no_of_failed_test = int(test_result.group(1))
        except Exception as err:
            print(err, source)
            print(">>>", proc.stdout.decode())
            print(">>>", proc.stderr.decode())
        

        unit_test = parse_tests(tcl_test)
        commented_out = 0
        for _, test in unit_test:
            if 'EXCLUDED' in test:
                commented_out += 1
        # print(source, no_of_unit_test, commented_out)

        # print(proc.stdout.decode())
        assert(no_of_failed_test == 0)

        total_mutants = 0
        succ_mutant = 0
        crash_mutant= 0
        pass_mutant = 0
        for mutants, unit in unit_test:
            if "EXCLUDED" in unit:
                continue
                
            with tempfile.TemporaryDirectory() as tempdir:
                shutil.copy2('tcl_testdir/malloc_common.tcl', tempdir)
                shutil.copy2('tcl_testdir/tester.tcl', tempdir)
                shutil.copy2('tcl_testdir/thread_common.tcl', tempdir)
                with open(os.path.join(tempdir, 'script.tcl'), 'w') as f:
                    f.write('set testdir [file dirname $argv0]\n')
                    f.write('source $testdir/tester.tcl\n')
                    f.write(unit)
                    f.write('\n')
                    f.write('finish_test')

                total_mutants += len(mutants)
                for mutant in mutants:
                    env_copy = os.environ.copy()
                    env_copy['DREDD_ENABLED_MUTATION'] = str(mutant)
                    proc = subprocess.run([textfixture_bin, 'script.tcl', '--verbose=0'], cwd=tempdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_copy)

                    if proc.returncode == 1:
                        succ_mutant += 1
                    elif proc.returncode != 0:
                        crash_mutant += 1
                    else:
                        pass_mutant += 1
                    # else:
                    #     print("fail adv", source, mutant)
        assert total_mutants == succ_mutant + crash_mutant + pass_mutant

        print(source, ' & ', no_of_unit_test, ' & ', commented_out, ' & ', succ_mutant, ' & ', crash_mutant, ' & ', pass_mutant, ' \\\\')
        total_no_of_unit_test += no_of_unit_test
        total_commented_out += commented_out
        total_total_mutants += total_mutants
        total_succ_mutant += succ_mutant
        total_crash_mutant += crash_mutant
        total_pass_mutant += pass_mutant

        
        
        # print(unit_test)
        # assert len(unit_test) == no_of_unit_test

        # break
        # with tempfile.TemporaryDirectory() as tmpdir:
        #     proc = subprocess.run([textfixture_bin, tcl_test], cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # if proc.returncode != 0:
        #     print(proc.returncode)
        #     print(proc.stdout.decode())
        #     print(proc.stderr.decode())

    print(total_no_of_unit_test, total_commented_out, total_succ_mutant, total_crash_mutant, total_pass_mutant)
if __name__ == '__main__':
    main()
    
