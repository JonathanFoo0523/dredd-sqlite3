from runner.dredd_test.regression_test import basic_slice_runner
from runner.common.types import TestStatus

# print(TestStatus.KILLED_FAIL.name)

with open('/home/ubuntu/dredd-sqlite3/sample_binary/ss_tests.txt') as test_files:
    tests = ['/home/ubuntu/sqlite-src/' + line.rstrip('\n') for line in test_files]

coverage_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_tracking'
mutation_bin = '/home/ubuntu/dredd-sqlite3/sample_binary/testfixture_alter_mutations'

with open('/home/ubuntu/dredd-sqlite3/sample_output/sample_output.csv', 'w') as output_file:
    with open('/home/ubuntu/dredd-sqlite3/sample_output/sample_killed.txt', 'w') as killed_file:
        basic_slice_runner(coverage_bin, mutation_bin, tests, output_file, killed_file)