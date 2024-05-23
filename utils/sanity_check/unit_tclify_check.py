import subprocess
import os
import argparse
import tempfile
import ast

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dredd_output_directory")
    parser.add_argument("tclify_output_directory")
    args = parser.parse_args()

    result = dict()

    for source in os.listdir(args.tclify_output_directory):
        source_full, ext = source.split('.')
        source = source.split('_')[0]

        if ext != 'test':
            continue

        if source.split('_')[0] in result:
            result[source.split('_')[0]][0] += 1
        else:
            result[source.split('_')[0]] = [1, 0, 0, 0]
        
        
        sqlite3_bin = os.path.abspath(os.path.join(args.dredd_output_directory, f'testfixture_{source}_mutation'))
        tcl_test = os.path.abspath(os.path.join(args.tclify_output_directory, f'{source_full}.test'))

        env_copy = os.environ.copy()
        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.run([sqlite3_bin, tcl_test], cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_copy)

        if proc.returncode != 0:
            print(f'Fail unmutated: {source_full}')
            print(proc.stderr)
        else:
            result[source.split('_')[0]][1] += 1

        with open(os.path.join(args.tclify_output_directory, source_full + '.test'), 'r') as f:
            for line in f.readlines():
                if line.startswith('# kill mutants'): 
                    advertised_kills = ast.literal_eval(line[len('# kill mutants '):])

            result[source.split('_')[0]][2] += len(advertised_kills) 

        for mutation_id in advertised_kills:
            env_copy["DREDD_ENABLED_MUTATION"] = str(mutation_id)
            with tempfile.TemporaryDirectory() as tmpdir:
                try:
                    proc = subprocess.run([sqlite3_bin, tcl_test], cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_copy, timeout=10)
                except:
                    pass

            if proc.returncode == 0:
                print(f'Fail mutated: {source}, {mutation_id}')
            else:
                result[source.split('_')[0]][3] += 1


    print(result)


if __name__ == '__main__':
    main()
    
