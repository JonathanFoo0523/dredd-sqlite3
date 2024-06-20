import subprocess
import os
import argparse
import tempfile
import re
import shutil
import pickle
import re

parser = argparse.ArgumentParser()
parser.add_argument("dredd_output_directory")
parser.add_argument("output_directory")
args = parser.parse_args()


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


def get_testcase_count(tcl_directory):

    return_testcases = dict()

    for source in sorted(os.listdir(tcl_directory)):
        source, ext = source.split('.')
        if ext != 'test':
            continue

        return_testcases[source] = []


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

        assert(no_of_failed_test == 0)

    
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

                effective_mutants = []
                for mutant in mutants:

                    env_copy = os.environ.copy()
                    env_copy['DREDD_ENABLED_MUTATION'] = str(mutant)
                    proc = subprocess.run([textfixture_bin, 'script.tcl', '--verbose=0'], cwd=tempdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_copy)

                    if proc.returncode == 0:

                        print(">>>", source, mutant)
                        continue

                    effective_mutants.append(mutant)                    

            return_testcases[source].append((effective_mutants, unit))
            
        
    return return_testcases


def total_unique(ll1, ll2, ll3):
    llres = []
    ll1_relative = dict()
    ll2_relative = dict()
    ll3_relative = dict()
    ll1_child = dict()
    ll2_child = dict()
    ll3_child = dict()
    all_mutants = set()

    for mutants, testcase in ll1:
        for mutant in mutants:
            ll1_relative[mutant] = mutants
            ll1_child[mutant] = testcase
            all_mutants.add(mutant)

    for mutants, testcase in ll2:
        for mutant in mutants:
            ll2_relative[mutant] = mutants
            ll2_child[mutant] = testcase
            all_mutants.add(mutant)

    for mutants, testcase in ll3:
        for mutant in mutants:
            ll3_relative[mutant] = mutants
            ll3_child[mutant] = testcase
            all_mutants.add(mutant)


    while len(all_mutants) > 0:
        mutant = next(iter(all_mutants))
        ll1_s = ll1_relative.get(mutant, [])
        ll2_s = ll2_relative.get(mutant, [])
        ll3_s = ll3_relative.get(mutant, [])
        max_t = max(len([s for s in ll1_s if s in all_mutants]), len([s for s in ll2_s if s in all_mutants]), len([s for s in ll3_s if s in all_mutants]))
        if len([s for s in ll1_s if s in all_mutants]) == max_t:
            all_mutants = all_mutants - set(ll1_s)
            llres.append((ll1_s, ll1_child[mutant]))
            print("ll1")
        elif len([s for s in ll2_s if s in all_mutants]) == max_t:
            all_mutants = all_mutants - set(ll2_s)
            llres.append((ll2_s, ll2_child[mutant]))
            print("ll2")
        elif len([s for s in ll3_s if s in all_mutants]) == max_t:
            all_mutants = all_mutants - set(ll3_s)
            llres.append((ll3_s, ll3_child[mutant]))
            print("ll3")
        else:
            raise "!!!"

    print(len(llres))
    return llres




        
# rand = get_testcase_count('../../sample_tclify_output_all')
# with open('rand_testcase_count.pkl', 'wb') as f:
#     pickle.dump(rand, f)
# print(rand)
# tlp = get_testcase_count('../../sample_tclify_output_tlp')
# with open('tlp_testcase_count.pkl', 'wb') as f:
#     pickle.dump(tlp, f)
# norec = get_testcase_count('../../sample_tclify_output_norec')
# with open('norec_testcase_count.pkl', 'wb') as f:
#     pickle.dump(norec, f)


with open('rand_testcase_count.pkl', 'rb') as f:
    rand = pickle.load(f)

with open('tlp_testcase_count.pkl', 'rb') as f:
    tlp = pickle.load(f)

with open('norec_testcase_count.pkl', 'rb') as f:
    norec = pickle.load(f)


for source in set([*rand.keys(), *tlp.keys(), *norec.keys()]):
    res = total_unique(rand.get(source, []), tlp.get(source, []), norec.get(source, []))

    with open(os.path.join(args.output_directory, source+'.test'), 'w') as f:
        f.write('set testdir [file dirname $argv0]\n')
        f.write('source $testdir/tester.tcl\n')
        f.write('\n')
        for i, (m, t) in enumerate(res):
            t = re.sub(r"(do_.*_test .*-dredd-)(\d+)(\.\d+ {)", lambda x: f"{x.group(1)}{i}{x.group(3)}", t)
            f.write(f'# kill mutants {[str(mm) for mm in m]}\n')
            f.write(t)
            f.write('\n\n')

        f.write('finish_test\n')



    

