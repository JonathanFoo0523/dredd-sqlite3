import pandas as pd
import argparse
import os
from pathlib import Path
import pickle

parser = argparse.ArgumentParser()
parser.add_argument("regress_directory",
                        help="Directory that contain regress_result",
                        type=Path)
parser.add_argument("fuzz_directory",
                        help="Directory that contain fuzz_result of fuzz_result of fuzz testing and interesting test cases",
                        type=Path)

args = parser.parse_args()

regress_result = dict()
try:
    with open(os.path.join(args.regress_directory, 'regression_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            # print(">>>", obj['source'], len(obj['killed']), obj['total'])
            # ['source', 'total', 'killed', 'in_coverage_survived', 'not_in_coverage']
            covered = set(range(0, obj['total'])) - obj['not_in_coverage']
            regress_result[obj['source']] = obj
            regress_result[obj['source']]['covered'] = covered
except EOFError:
    pass

# Load from global fuzzing checkpoint
fuzz_result = dict()
try:
    with open(os.path.join(args.fuzz_directory, 'fuzzing_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            if obj['gen'] != 8:
                continue
            # print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")

            fuzz_result[obj['source']] = obj                
except EOFError as err:
    pass



total_fuzz_covered = 0
total_newly_covered_by_regres = 0
total_previously_covered_by_regress = 0

total_fuzz_killed = 0
total_kill_in_newly_covered = 0
total_kill_in_regress_covered = 0

for file in regress_result:
    if file not in fuzz_result:
        continue # zero covered

    # should be empty set by design (correct)
    assert len(regress_result[file]['killed'].intersection(fuzz_result[file]['cum_kill'].keys())) == 0

    # fuzz_covered, newly_covered_by_regres, previously_covered_by_regress (correct)
    newly_covered_by_fuzz = fuzz_result[file]['cum_coverage'] - regress_result[file]['covered']
    previously_covered_by_regress = fuzz_result[file]['cum_coverage'].intersection(regress_result[file]['covered'])
    # print(len(fuzz_result[file]['cum_coverage']), len(newly_covered_by_fuzz), len(previously_covered_by_regress))

    # fuzz_killed, fuzz_kill(regress covered), fuzz_kill(regress not covered)
    fuzz_kill = set(fuzz_result[file]['cum_kill'].keys())
    kill_in_newly_covered = newly_covered_by_fuzz.intersection(fuzz_kill)
    kill_in_regress_covered = previously_covered_by_regress.intersection(fuzz_kill)
    # print(len(fuzz_result[file]['cum_kill']), len(kill_in_regress_covered), len(kill_in_newly_covered))

    total_fuzz_covered += len(fuzz_result[file]['cum_coverage'])
    total_newly_covered_by_regres += len(newly_covered_by_fuzz)
    total_previously_covered_by_regress += len(previously_covered_by_regress)

    total_fuzz_killed += len(fuzz_result[file]['cum_kill'])
    total_kill_in_newly_covered += len(kill_in_newly_covered)
    total_kill_in_regress_covered += len(kill_in_regress_covered)

print(total_fuzz_covered, total_newly_covered_by_regres, total_previously_covered_by_regress)
print(total_fuzz_killed, total_kill_in_newly_covered, total_kill_in_regress_covered)
print(total_fuzz_covered - total_fuzz_killed, total_newly_covered_by_regres - total_kill_in_newly_covered, total_previously_covered_by_regress - total_kill_in_regress_covered)








# fuzz_covered_mutants = dict()
# fuzz_killed_mutants = dict()
# for file in sorted(os.listdir(args.fuzz_directory)):
#     if not os.path.isfile(os.path.join(args.fuzz_directory, file)):
#         continue
#     if file.split('.')[-1] != 'csv':
#         continue

#     df = pd.read_csv(os.path.join(args.fuzz_directory, file))
#     mutants = df[' mutant']
#     mutants.unique()

#     killed_mutants = df.loc[df[' status'] == ' KILLED_FAILED', ' mutant']
#     killed_mutants.unique()
#     fuzz_killed_mutants[file] = set(killed_mutants)
#     print(file, len(killed_mutants), len(mutants))

#     # killed_mutants = df.loc[df[]]

#     fuzz_covered_mutants[file] = set(mutants)
#     break


# print(6146 in fuzz_killed_mutants['alter_output.csv'])
# print(fuzz_result[file][8][0].keys())
# print(len(fuzz_covered_mutants['alter_output.csv']), len(set(fuzz_result[file][8][1])))
# print('l', fuzz_covered_mutants['alter_output.csv'] - fuzz_result[file][8][1])
# print("Fuzz Covered Mutants", fuzz_covered_mutants)
