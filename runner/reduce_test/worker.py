import os
import pickle
import asyncio

class TestReductionWorker:
    def __init__(self, generation_directory):
        self.generation_directory = generation_directory

    def runner(self):
        # Load from global fuzzing checkpoint
        generation_result = dict()
        try:
            with open(os.path.join(self.generation_directory, 'fuzzing_test.pkl'), 'rb') as f:
                while True:
                    obj = pickle.load(f)
                    source_name = obj['source']
                    if source_name not in generation_result:
                        generation_result[source_name] = (obj['gen'], obj['cum_kill'])
                    elif generation_result[source_name][0] < obj['gen']:
                        generation_result[obj['source']] = (obj['gen'], obj['cum_kill'])
        except EOFError as err:
            pass

        # Initialize queue
        queue = asyncio.Queue()
        for (source, (_, kill_dict)) in generation_result.items():
            for (mutant, test_case) in kill_dict.items():
                queue.put_nowait((source, mutant, test_case))

        # print(generation_result)