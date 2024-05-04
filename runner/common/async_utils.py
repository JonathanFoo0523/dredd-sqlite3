import asyncio
import psutil
import subprocess
import os
import signal

TIMEOUT_RETCODE = 124   # Same as UNIX tiemout return code


# Extend asyncio.create_subprocess_exec with timeout, so it function similarly as subprocess.run()
async def subprocess_run(args, timeout=None, stdin=None, input=None, stdout=None, stderr=None, **kwargs):
    proc = await asyncio.create_subprocess_exec(*args, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True, **kwargs)

    try:
        stdout, stderr =  await asyncio.wait_for(proc.communicate(input), timeout=timeout)
    except asyncio.TimeoutError:
        # if proc.returncode is None:
        #     try:
        #         parent = psutil.Process(proc.pid)
        #         for child in parent.children(recursive=True):
        #             try:
        #                 child.terminate()
        #             except:
        #                 pass
        #         parent.terminate()
        #     except:
        #         pass
        return ("", f'Timeout after {timeout}s'.encode(), TIMEOUT_RETCODE)
    finally:
        if proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except:
                pass
            # proc.terminate()

    return (stdout, stderr, proc.returncode)
