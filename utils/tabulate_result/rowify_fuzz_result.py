import os
import argparse
from pathlib import Path
import pickle

parser = argparse.ArgumentParser()
parser.add_argument("output_directory",
                        help="Directory that contain result of result of fuzz testing and interesting test cases",
                        type=Path)
args = parser.parse_args()

# Load from global fuzzing checkpoint
result = dict()
try:
    with open(os.path.join(args.output_directory, 'fuzzing_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            # print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")
            if obj['source'] not in result:
                result[obj['source']] = dict()

            result[obj['source']][obj['gen']] = (len(obj['cum_kill']), len(obj['cum_coverage']))                
except EOFError as err:
    pass

# for i in [1, 2, 4 8]:

for file in sorted(result):
    print(file.replace("_", "\_" )  + ' & '
            + f'{result[file][1][0]} & {result[file][1][1]}' + ' & '
            + f'{result[file][2][0]} & {result[file][2][1]}' + ' & '
            + f'{result[file][4][0]} & {result[file][4][1]}' + ' & '
            + f'{result[file][8][0]} & {result[file][8][1]}' + ' \\\\'
        )

