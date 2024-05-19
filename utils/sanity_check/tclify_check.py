import subprocess
import os
import argparse
import tempfile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("dredd_output_directory")
    parser.add_argument("tclify_output_directory")
    args = parser.parse_args()

    for source in os.listdir(args.tclify_output_directory):
        source, ext = source.split('.')
        if ext != 'test':
            continue

        sqlite3_bin = os.path.abspath(os.path.join(args.dredd_output_directory, f'testfixture_{source}_mutation'))
        tcl_test = os.path.abspath(os.path.join(args.tclify_output_directory, f'{source}.test'))

        with tempfile.TemporaryDirectory() as tmpdir:
            proc = subprocess.run([sqlite3_bin, tcl_test], cwd=tmpdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if proc.returncode != 0:
            print(proc.stdout.decode())

if __name__ == '__main__':
    main()
    
