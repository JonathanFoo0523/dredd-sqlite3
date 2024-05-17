import re
import os
import argparse

from queue import PriorityQueue

pq = PriorityQueue()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sqlite_src", help="Directory that contains sqlite test/ directory and ext/ directory")
    parser.add_argument("testfixture_output", help="Output path of testfixture run with --verbose=0")
    parser.add_argument("output_path", help="Output path of list of test")
    parser.add_argument("sort", help="Wheter to sort by alphabet or by duration", default='duration')
    args = parser.parse_args()

    assert args.sort == 'duration' or args.sort == 'alphabet' 

    with open(args.testfixture_output, 'r') as f:
        for line in f.readlines():
            if "Time:" not in line:
                continue
            
            match = re.search(r'Time: (.*) (\d+) ms', line.rstrip('\n'))
            file, time = (match.group(1), match.group(2))

            if os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'rtree', file)):
                filepath = os.path.join('ext', 'rtree', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'fts5', 'test', file)):
                filepath = os.path.join('ext', 'fts5', 'test', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'expert', file)):
                filepath = os.path.join('ext', 'expert', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'lsm1', 'test', file)):
                filepath = os.path.join('ext', 'lsm1', 'test', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'recover', file)):
                filepath = os.path.join('ext', 'recover', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'rbu', file)):
                filepath = os.path.join('ext', 'rbu', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'ext', 'session', file)):
                filepath = os.path.join('ext', 'session', file)
            elif os.path.isfile(os.path.join(args.sqlite_src, 'test', file)):
                filepath = filepath = os.path.join('test', file)
            else:
                print(file)
                raise "Unknown directory"

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

    

