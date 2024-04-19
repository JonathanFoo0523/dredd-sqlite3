import tempfile
from distutils.dir_util import copy_tree
import shutil
import os
import subprocess


class DreddAndCompileWorker:
    def __init__(self, self.tree_src_dir: str, self.res_dir: str):
        self.self.tree_src_dir = tree_src_dir
        self.self.res_dir = res_dir

    def run(self, file: str) -> str:
        with tempfile.TemporaryDirectory() as temp_src_dir:
            copy_tree(self.tree_src_dir, temp_src_dir)

            # Keep a clean copy of file
            shutil.copy(f'{temp_src_dir}/{file}', f'{temp_src_dir}/clean_{file}')

            # Apply mutation to source file
            subprocess.run([DREDD_EXECUTABLE, file, '--mutation-info-file', f'{self.res_dir}/{file}_mutation_info.json'], cwd=temp_src_dir)
            subprocess.run(['tclsh', 'tool/mksqlite3c.tcl'], cwd=temp_src_dir)

            # Compile testfixture mutation
            subprocess.run(['make', 'testfixture'], stdout=subprocess.DEVNULL, cwd=temp_src_dir)
            shutil.copy(f'{temp_src_dir}/testfixture', f'{self.res_dir}/testfixture_${FILE_NAME}_mutation')

            # Compile sqlite3 shell mutation
            subprocess.run(['make', 'sqlite3'], stdout=subprocess.DEVNULL, cwd=temp_src_dir)
            shutil.copy(f'{temp_src_dir}/sqlite3', f'{self.res_dir}/sqlite3_${FILE_NAME}_mutation')

            # Reset file
            shutil.copy(f'{temp_src_dir}/clean_{file}', f'{temp_src_dir}/{file}')

            # Apply mutants coverage to source file
            subprocess.run([DREDD_EXECUTABLE, '--only-track-mutant-coverage', file, '--mutation-info-file', f'temp.json'], cwd=temp_src_dir)
            subprocess.run(['tclsh', 'tool/mksqlite3c.tcl'], cwd=temp_src_dir)

            # Compile testfixture tracking
            subprocess.run(['make', 'testfixture'], stdout=subprocess.DEVNULL, cwd=temp_src_dir)
            shutil.copy(f'{temp_src_dir}/testfixture', f'{self.res_dir}/testfixture_${FILE_NAME}_tracking')

            # Compile sqlite3 shell tracking
            subprocess.run(['make', 'sqlite3'], stdout=subprocess.DEVNULL, cwd=temp_src_dir)
            shutil.copy(f'{temp_src_dir}/sqlite3', f'{self.res_dir}/sqlite3_${FILE_NAME}_tracking')

        return file















