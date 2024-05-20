import re
import os
import argparse

from queue import PriorityQueue

pq = PriorityQueue()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("testrunner_output", help="Output path of testrunner.tcl")
    parser.add_argument("output_path", help="Output path of list of test")
    parser.add_argument("sort", help="Wheter to sort by alphabet or by duration", default='duration')
    args = parser.parse_args()

    assert args.sort == 'duration' or args.sort == 'alphabet' 

    with open(args.testrunner_output, 'r') as f:
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

    with open(args.output_path, 'w+') as f:
        if args.sort == 'duration':
            while not pq.empty():
                item = pq.get()
                f.write(item[1])
                f.write('\n')
        else:
            for test in sorted([t[1] for t in pq.queue]):
                f.write(test)
                f.write('\n')

if __name__ == "__main__":
    main()

    

