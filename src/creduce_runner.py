import subprocess
import os
from tqdm import tqdm

files = [f for f in os.listdir('sqlancer_runner_res') if os.path.isfile('sqlancer_runner_res/'+f)]

for file in tqdm(files):
    # Extract Mutation ID
    mutation_id = int(file.split('_')[1].split('.')[0])

    # Copy Original file to creduce_runner_res
    subprocess.run(['cp', f'sqlancer_runner_res/{file}', 'creduce_runner_res'])

    # Create and write interestingness test
    with open(f'creduce_runner_res/interestingness_{file.split(".")[0]}.sh', 'w') as f:
        f.write('#!/bin/bash\n')
        f.write(f'python3 /home/jjf120/dredd_exp/creduce_differential.py {file} {mutation_id}\n')

    os.system(f"chmod +x creduce_runner_res/interestingness_{file.split('.')[0]}.sh")

    # CReduce
    try:
        subprocess.run(['creduce', f"interestingness_{file.split('.')[0]}.sh", file], cwd='creduce_runner_res')
    except Exception as err:
        print(err)

    os.remove(f'creduce_runner_res/interestingness_{file.split(".")[0]}.sh')

