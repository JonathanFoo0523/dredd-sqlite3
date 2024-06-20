import pandas as pd
import argparse
import os
from pathlib import Path
import pickle


random_result = dict()
try:
    with open(os.path.join('../../sample_fuzzing_output_all', 'fuzzing_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            if obj['gen'] != 8:
                continue
            # print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")

            random_result[obj['source']] = obj                
except EOFError as err:
    pass


tlp_result = dict()
try:
    with open(os.path.join('../../sample_fuzzing_output_tlp', 'fuzzing_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            if obj['gen'] != 8:
                continue
            # print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")

            tlp_result[obj['source']] = obj                
except EOFError as err:
    pass

norec_result = dict()
try:
    with open(os.path.join('../../sample_fuzzing_output_norec', 'fuzzing_test.pkl'), 'rb') as f:
        while True:
            obj = pickle.load(f)
            if obj['gen'] != 8:
                continue
            # print(f"Source: {obj['source']}; Gen: {obj['gen']}; New Kill: {len(obj['cum_kill'])}; Covered: {len(obj['cum_coverage'])};")

            norec_result[obj['source']] = obj                
except EOFError as err:
    pass

import heapq

list = []
for file in random_result:
    min_k = min(len(random_result[file]['cum_kill']), len(tlp_result[file]['cum_kill']), len(norec_result[file]['cum_kill']))
    max_k = max(len(random_result[file]['cum_kill']), len(tlp_result[file]['cum_kill']), len(norec_result[file]['cum_kill']))

    list.append((((max_k - min_k) / min_k) if min_k else 0, file))

heapq.heapify(list)
to_list = heapq.nsmallest(10, list)

print('Random', 'TLP', 'NoREC')
for _, file in to_list:
    print(file, len(random_result[file]['cum_kill']), len(random_result[file]['cum_coverage']), len(tlp_result[file]['cum_kill']), len(tlp_result[file]['cum_coverage']), len(norec_result[file]['cum_kill']), len(norec_result[file]['cum_coverage']))
    