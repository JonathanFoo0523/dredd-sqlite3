from runner.common.async_utils import subprocess_run, TIMEOUT_RETCODE
from runner.common.constants import TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST

import os
import pickle
import asyncio
import jinja2
import tempfile
import stat

class TestReductionWorker:
    def __init__(self, mutation_binary, generation_directory, output_dir, max_parallel_tasks=4):
        self.mutation_binary = os.path.abspath(mutation_binary)
        self.generation_directory = generation_directory
        self.output_dir = output_dir
        self.max_parallel_tasks = max_parallel_tasks


    async def reduction_queue_consumer(self, queue: asyncio.Queue):
        while True:
            source, mutant, testcase = await queue.get()

            interestingness_test_template = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                searchpath=os.path.dirname(os.path.realpath(__file__)))).get_template("interesting.py.jinja")

            # with tempfile.TemporaryDirectory() as tempdir:
            tempdir = self.output_dir
            open(os.path.join(tempdir, 'interesting.py'), 'w').write(interestingness_test_template.render(
                sqlite3_mutation_binary=os.path.join(self.mutation_binary, f'sqlite3_{source}_mutation'),
                mutation_id = mutant,
                testcase_to_check = f'database_{testcase}.log',
                timeout_multiplier = TIMEOUT_MULTIPLIER_FOR_DIFFERENTIAL_TEST,
            ))

            # Make the interestingness test executable
            st = os.stat(os.path.join(tempdir, 'interesting.py'))
            os.chmod(os.path.join(tempdir, 'interesting.py'), st.st_mode | stat.S_IEXEC)

            # Execute 
            statements_path = os.path.join(self.generation_directory, 'interesting_test_dir', f'database_{testcase}.log')
            proc = await subprocess_run(['creduce', 'interesting.py', statements_path], cwd=tempdir)
            print(proc)
            exit(0)


    async def runner(self):
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
            for (mutant, testcase) in kill_dict.items():
                queue.put_nowait((source, mutant, testcase))

        consumers = [asyncio.create_task(self.reduction_queue_consumer(queue)) for _ in range(self.max_parallel_tasks)]
        await queue.join()

        for task in consumers:
            task.cancel()



        # print(generation_result)