import tempfile
from distutils.dir_util import copy_tree
import shutil
import os
import subprocess
from enum import Enum


DreddType = Enum('DreddType', ['coverage', 'mutation'])


class DreddAndCompileWorker:
    def __init__(self, dredd_src_path, tree_src_dir: str, res_dir: str):
        self.dredd_src_path = dredd_src_path
        self.tree_src_dir = tree_src_dir
        self.res_dir = res_dir
        self.dredd_executable = os.path.join(dredd_src_path, 'third_party', 'clang+llvm', 'bin', 'dredd')

    def prepare_compilation_database(self, target: str, src_path: str):
        subprocess.run(['make', target], stdout=subprocess.DEVNULL, cwd=src_path)
        result = subprocess.run(['sed', '-e', r'1s/^/[\n/', '-e', r'$s/,$/\n]/', 'cd.json'], capture_output=True, text=True, check=True, cwd=src_path)
        with open(f'{src_path}/compile_commands.json', 'w+') as f:
            f.write(result.stdout)

    def mutate_and_compile(self, file_abs_path: str, src_dir: str, dredd_type: DreddType, target: str):
        file_wo_extension = file_abs_path.split('/')[-1].split('.')[0]
        mutation_info_path = f'{self.res_dir}/{file_wo_extension}_{target}_info.json'

        # Apply mutation to source file
        if dredd_type == DreddType.coverage:
            proc = subprocess.run([self.dredd_executable, '--only-track-mutant-coverage', file_abs_path, '--mutation-info-file', mutation_info_path], stderr=subprocess.PIPE, cwd=src_dir)
        else:
            proc = subprocess.run([self.dredd_executable , file_abs_path, '--mutation-info-file', mutation_info_path], stderr=subprocess.PIPE, cwd=src_dir)

        # check that dredd success
        if proc.returncode != 0:
            print(proc.stderr)
            raise Exception(f"Dredd fail with code {proc.returncode}")

        # Compose sqlite3.c file
        proc = subprocess.run(['tclsh', 'tool/mksqlite3c.tcl'], cwd=src_dir)
        if proc.returncode != 0:
            raise Exception(f"Compose sqlite3 with failed code {proc.returncode}")

        # Compile testfixture mutation/coverage
        proc = subprocess.run(['make', target], stdout=subprocess.DEVNULL, cwd=src_dir, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise Exception(f"Compile mutated sqlite3 failed with code {proc.returncode}")

        # Save the target binary in result directory
        shutil.copy(f'{src_dir}/{target}', f'{self.res_dir}/{target}_{file_wo_extension}_{dredd_type.name}')

        # (Optional) Accounting purpose
        shutil.copy(f'{src_dir}/sqlite3.c', f'{self.res_dir}/{target}_{file_wo_extension}_sqlite3.c')

    
    def run(self, file: str, target: str) -> str:
        file_wo_extension = file.split('.')[0]
        with tempfile.TemporaryDirectory() as temp_src_dir:
            file_abs_path = f'{temp_src_dir}/tsrc/{file}'
            
            copy_tree(self.tree_src_dir, temp_src_dir)

            # Keep a clean copy of file
            shutil.copy(file_abs_path, f'{temp_src_dir}/clean_{file}')

            self.prepare_compilation_database(target, temp_src_dir)
            self.mutate_and_compile(file_abs_path, temp_src_dir, DreddType.mutation, target)
            shutil.copy(f'{temp_src_dir}/clean_{file}', file_abs_path) # Reset file
            self.mutate_and_compile(file_abs_path, temp_src_dir, DreddType.coverage, target)

            # # Reset file
            # subprocess.run(['make', 'clean'], stdout=subprocess.DEVNULL, cwd=src_dir)

            # print(">>>>>2.5")
            # self.prepare_compilation_database('sqlite3', temp_src_dir)
            # print(">>>>>3")
            # self.mutate_and_compile(file_abs_path, temp_src_dir, DreddType.mutation, 'sqlite3')
            # shutil.copy(f'{temp_src_dir}/clean_{file}', file_abs_path) # Reset file
            # self.mutate_and_compile(file_abs_path, temp_src_dir, DreddType.coverage, 'sqlite3')

        return file

    def run_mp_wrapper(self, input: tuple[str, str]):
        file, target = input
        self.run(file, target)















