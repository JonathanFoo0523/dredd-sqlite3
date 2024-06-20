import subprocess
import os
import argparse
import tempfile
import re

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

parser = argparse.ArgumentParser()
parser.add_argument("dredd_output_directory")
args = parser.parse_args()

def get_testcase_count(tcl_directory):
    valid_test_case = dict()
    excluded_test_case = dict()
    test_cases_tuple = dict()
    for source in sorted(os.listdir(tcl_directory)):
        source, ext = source.split('.')
        if ext != 'test':
            continue

        # if source != 'alter':
            # continue
        # print(source)
        textfixture_bin = os.path.abspath(os.path.join(args.dredd_output_directory, f'testfixture_{source}_mutation'))
        tcl_test = os.path.abspath(os.path.join(tcl_directory, f'{source}.test'))
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
        
        valid_test_case[source] = no_of_unit_test
        excluded_test_case[source] = commented_out
        test_cases_tuple[source] = unit_test
        # print(source, no_of_unit_test, commented_out)

        # print(proc.stdout.decode())
        assert(no_of_failed_test == 0)

    return valid_test_case, excluded_test_case, test_cases_tuple

def total_unnique(ll1, ll2, ll3):
    mutants = set([m for ll in [ll1, ll2, ll3] for g, tt in ll for m in g])


    for mutant in mutants:
        pass
    # print(len(total))
        
rav, rae, ll1 = get_testcase_count('../../sample_tclify_output_all')
tv, te, ll2 = get_testcase_count('../../sample_tclify_output_tlp')
nv, ne, ll3 = get_testcase_count('../../sample_tclify_output_norec')


for source in rav:
    total_unnique(ll1.get(source, []), ll2.get(source, []), ll3.get(source, []))

    print(source,  ' & ', 
          rav.get(source, 0), ' & ',
          rae.get(source, 0), ' & ',
          tv.get(source, 0), ' & ',
          te.get(source, 0), ' & ',
          nv.get(source, 0), ' & ',
          ne.get(source, 0), ' & ', 0, ' \\\\')
