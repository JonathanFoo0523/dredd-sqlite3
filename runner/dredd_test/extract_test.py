import tempfile
import subprocess
import os
import re
from queue import PriorityQueue

class TestExtractor:
    def __init__(self, sqlite_src, testfixture_path, subset, max_parallel_tasks=4):
        self.sqlite_src = os.path.abspath(sqlite_src)
        self.testfixture_path = os.path.abspath(testfixture_path)
        self.subset = subset
        self.max_parallel_tasks = max_parallel_tasks

    def extract(self):
        result = []
        with tempfile.TemporaryDirectory(prefix='dredd-sqlite3-dredd-test-extractor') as tempdir:
            testrunner_path = os.path.join(self.sqlite_src, 'test', 'testrunner.tcl')
            proc = subprocess.run([self.testfixture_path, testrunner_path, self.subset, '--jobs', str(self.max_parallel_tasks)], stdout=subprocess.DEVNULL, cwd=tempdir)

            if proc.returncode != 0:
                raise Exception(f"TestExtractor: testrunner failed with excitcode: {proc.returncode}")

            pq = PriorityQueue()
    
            with open(os.path.join(tempdir, 'testrunner.log'), 'r') as f:
                for line in f.readlines():
                    if '###' not in line:
                            continue
                    match = re.search(r'###( config=.*)? (.*) (\d+)ms \(done\)', line.rstrip('\n'))
                    try:
                        filepath, time = (match.group(2), match.group(3))
                    except Exception as err:
                        print(line, match.group(0))
                        raise err

                    pq.put((int(time), filepath))

            while not pq.empty():
                item = pq.get()
                result.append(item[1])

        return result




