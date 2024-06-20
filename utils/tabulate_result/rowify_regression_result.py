import os
import argparse
from pathlib import Path
import pickle

parser = argparse.ArgumentParser()
parser.add_argument("output_directory",
                        help="Directory that contains result of regression/mutation testing.",
                        type=Path)
args = parser.parse_args()

# Load from global regression checkpoint
result = dict()
try:
    with open(os.path.join(args.output_directory, 'regression_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            # print(">>>", obj['source'], len(obj['killed']), obj['total'])
            covered = obj['total'] - len(obj['not_in_coverage'])
            result[obj['source']] = (obj['total'], covered, len(obj['killed']))
except EOFError:
    pass

total_covered = 0
total_killed = 0
total_mutants = 0
for file in sorted(result):
    total_covered += result[file][1]
    total_killed += result[file][2]
    total_mutants += result[file][0]
    print(file.replace("_", "\_" ) + ' & '
            + str(result[file][0]) + ' & '
            + str(result[file][1]) + ' & '
            + str(result[file][2]) + ' \\\\'
        )

print()
print(total_killed, total_covered, total_mutants)