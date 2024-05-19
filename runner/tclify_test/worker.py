import os
import hashlib
import re
import subprocess
import asyncio
import tempfile
import json

class TCLifyWorker:
    def __init__(self, mutation_dir, reduction_dir, output_dir):
        self.mutation_dir = mutation_dir
        self.reduction_dir = reduction_dir
        self.output_dir = output_dir

    def get_file_hash(self, file):
        md5 = hashlib.md5()
        with open(file, 'r') as f:
            for line in f.readlines():
                md5.update(line.rstrip('\n').encode())
        return md5.hexdigest()

    async def readline(self, stream: asyncio.StreamReader, timeout: float):
        try:
            return await asyncio.wait_for(stream.read(1024), timeout=timeout)
        except asyncio.TimeoutError:
            return None


    def parse_stderr(self, err_msg):
        err_msg = err_msg.replace(' (19)', '')
        match = re.search(r'(.*) error near line (\d+): (.*)', err_msg)
        try:
            res = match.group(3)
        except:
            res = err_msg
        return res

    def parse_stdout(self, json_str):
        json_str = json_str.replace('\n', '')
        json_obj = json.loads(json_str)

        res = []
        for row in json_obj:
            for col in row:
                if row[col] is None or row[col] == '':
                    res.append(str('{}'))
                elif type(row[col]) is str and ' ' in row[col]:
                    res.append('{' + str(row[col]) + '}')
                else:
                    res.append(str(row[col]))

        return ' '.join(res)

    async def group_sql(self, file, source):
        with tempfile.NamedTemporaryFile(prefix='dredd-sqlite3-tcl-test', suffix='.db') as tempdbfile:
            proc = await asyncio.create_subprocess_exec(os.path.join(self.mutation_dir, f'sqlite3_{source}_mutation'), tempdbfile.name, '-json', stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
            res = []
            with open(file, 'r') as f2:
                sql_buffer = []
                for sql in f2.readlines():
                    proc.stdin.write(sql.encode())
                    await proc.stdin.drain()

                    stdout = await self.readline(proc.stdout, timeout=0.01)
                    stderr = await self.readline(proc.stderr, timeout=0.01)

                    if stdout:
                        stdout = self.parse_stdout(stdout.decode())
                        # stdout = stdout.decode()
                    if stderr:
                        stderr = self.parse_stderr(stderr.decode())

                    sql_buffer.append(sql)
                    if stdout is not None or stderr is not None:
                        res.append((sql_buffer, (stdout, stderr)))
                        sql_buffer = []
                if len(sql_buffer) > 0:
                    res.append((sql_buffer, (stdout, stderr)))
            await proc.communicate('.quit\n'.encode())
        return res


    async def runner(self, source):
        testcase_mutants_dict = dict()
        for file in os.listdir(os.path.join(self.reduction_dir, source)):
            abs_file_path = os.path.abspath(os.path.join(self.reduction_dir, source, file))
            hash = self.get_file_hash(abs_file_path)
            mutant = re.search(r'testcase_(\d+).log', file).group(1)
            if hash in testcase_mutants_dict:
                testcase_mutants_dict[hash].append(mutant)
            else:
                testcase_mutants_dict[hash] = [mutant]

        with open(os.path.join(self.output_dir, f'{source}.test'), 'w+') as f:
            f.write('set testdir [file dirname $argv0]\n')
            f.write('source $testdir/tester.tcl\n\n')
            for j, mutants in enumerate(testcase_mutants_dict.values()):
                file_path = os.path.join(self.reduction_dir, source, f'testcase_{mutants[0]}.log')
                try:
                    groups = await self.group_sql(file_path, source)
                except Exception as err:
                    print(err, source, mutants[0])
                    return
                f.write(f'# kill mutants {sorted(mutants)}\n')
                f.write('reset_db\n')
                f.write('sqlite3_db_config db DEFENSIVE 1\n')
                for i, (sqls, (stdout, stderr)) in enumerate(groups):
                    if stderr is not None:
                        f.write(f'do_catchsql_test {source}-dredd-{j+1}.{i+1}' + ' {\n')
                        f.write('  ')
                        f.write('  '.join(sqls))
                        f.write('} {1 {' + stderr + '}}\n')
                    else:
                        f.write(f'do_execsql_test {source}-dredd-{j+1}.{i+1}' + ' {\n')
                        f.write('  ')
                        f.write('  '.join(sqls))
                        f.write('} {' + (stdout if stdout else "") + '}\n')


                f.write('\n')
            f.write('finish_test\n')

    def mpwrap_runner(self, source):
        asyncio.run(self.runner(source))



