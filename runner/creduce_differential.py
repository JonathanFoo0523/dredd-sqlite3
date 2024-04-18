import sys
import os
import subprocess


def differential_test(input_file, mutation_id, print_diff=False):
    if os.path.exists("temp_ref.db"):
        os.remove("temp_ref.db")
    if os.path.exists("temp_mut.db"):
        os.remove("temp_mut.db")

    different = False
    diff_line = -1

    my_env = os.environ.copy()
    p_ref = subprocess.Popen(['/home/jjf120/sqlite-src-3450200/sqlite3', "temp_ref.db"],
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        # text=True, 
        env = my_env,
        # errors='replace'
    )

    my_env["DREDD_ENABLED_MUTATION"] = str(mutation_id)
    p_mut = subprocess.Popen(['/home/jjf120/sqlite-src-3450200/sqlite3', "temp_mut.db"],
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        # text=True, 
        env = my_env,
        # errors='replace'
    )

    with open(input_file, "rb") as f:
        s = f.read()
        while s[-1] != 59:
            s = s[:-1]
        res_ref, err_ref = p_ref.communicate(s)
        res_mut, err_mut = p_mut.communicate(s)

    os.remove("temp_ref.db")
    os.remove("temp_mut.db")

    return res_ref != res_mut or err_ref != err_mut or p_ref.returncode != p_mut.returncode

if differential_test(sys.argv[1], sys.argv[2]):
    exit(0)
else:
    exit(1)