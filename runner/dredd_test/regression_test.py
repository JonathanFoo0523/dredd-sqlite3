import tempfile
import time
import os
import subprocess
import re

from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST
from runner.common.types import MutantID, TestStatus


def get_mutations_in_coverage_by_test(tracking_binary: str, test_path: str) -> set[MutantID]:
    with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-dredd-test') as temp_coverage_file:
        coverage_filepath = temp_coverage_file.name
        env_copy = os.environ.copy()
        env_copy["DREDD_MUTANT_TRACKING_FILE"] = coverage_filepath

        try:
            with tempfile.TemporaryDirectory() as temp_test_dir:
                subprocess.run([tracking_binary, test_path], env=env_copy, stdout=subprocess.DEVNULL, cwd=temp_test_dir)
        except Exception as err:
            print(err)
            exit(1)

        temp_coverage_file.seek(0)
        covered_mutants = [int(line.rstrip()) for line in temp_coverage_file]

    return covered_mutants


def run_testfixture(testfixture_binary: str, test_path: str, mutant: MutantID = None, timeout: float = None) -> (TestStatus, str):
    env_copy = os.environ.copy()
    if mutant is not None:
        env_copy["DREDD_ENABLED_MUTATION"] = str(mutant)
    
    try:
        with tempfile.TemporaryDirectory() as temp_test_dir:
            result = subprocess.run([testfixture_binary, test_path], timeout=timeout, env=env_copy, capture_output=True, text=True, check=True, cwd=temp_test_dir)
    except Exception as e:
        description = ' '.join(str(e).split()[3:])
        status = TestStatus.KILLED_TIMEOUT if e is subprocess.TimeoutExpired else TestStatus.KILLED_FAIL
        return (status, description)

    output = ''.join(result.stdout)
    match = re.search('(\d)+ errors out of (\d)+', output)
    description = match.group() if match is not None else output
    return (TestStatus.SURVIVED, description)


def basic_slice_runner(coverage_binary: str, mutation_binary: str, testset: list[str], outputfile, killedfile):
    outputfile.write(f"status, test_name, mutant_id, description\n")
    killed = set()

    for index, test in enumerate(testset):
        print("Running:", test, f"{index + 1}/{len(testset)}")

        start = time.time()
        mutants = get_mutations_in_coverage_by_test(coverage_binary, test)
        end = time.time()
        base_time = end - start
        print(f"Time: {base_time}s")

        print("Number of mutants in coverage", len(mutants))

        if len(mutants) == 0:
            print()
            continue        

        killCount = 0
        surviveCount = 0
        skipCount = 0
        totalCount = 0
        
        for mutant in mutants:
            totalCount += 1

            if mutant in killed:
                skipCount += 1
                print(f"Killed: {killCount}, Survived: {surviveCount}, Skipped: {skipCount}", end='\r' if len(mutants) != totalCount else '\n')
                continue

            status, description = run_testfixture(mutation_binary, test, mutant=mutant, timeout=base_time * TIMEOUT_MULTIPLIER_FOR_REGRESSION_TEST)
            if status == TestStatus.SURVIVED:
                surviveCount += 1
            else:
                killCount += 1
                killedfile.write(f"{mutant}\n")
                killed.add(mutant)

            outputfile.write(f"{status.name}, {test[24:]}, {mutant}, {description}\n")
            print(f"Killed: {killCount}, Survived: {surviveCount}, Skipped: {skipCount}", end='\r' if len(mutants) != totalCount else '\n')

        print()



# def getTestSet(testlist):
#     res = []
#     with open(testlist, "r") as f:
#         for line in f:
#             res.append(line.rstrip('\n'))
#     return res


# def extractErrorCount(output):
#     for line in iter(output.splitlines()):
#         if "errors out of" in line:
#             return line
#     return ""

# csvfile = ""
# try:
#     mutation = sys.argv[1]
#     coverage = sys.argv[2]
#     tests = sys.argv[3]
#     opts, args = getopt.getopt(sys.argv[4:],"ho:k:")
# except getopt.GetoptError:
#     print ('sampleMutation.py mutation coverage tests -o <csvfile> -k <killedfile>')
#     sys.exit(2)


# for opt, arg in opts:
#     if opt == '-h':
#         print('sampleMutation.py mutation coverage tests -o <csvfile> -k <killedfile>')
#         sys.exit()
#     elif opt == '-o':
#         csvfile = arg
#     elif opt == '-k':
#         killedfile = arg

# f = open(csvfile, "w")
# f2 = open(killedfile, "a")
# test = getTestSet(tests)
# runTests(coverage, mutation, test, f, f2)
# f.close()
# f2.close()