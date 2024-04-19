import asyncio
import psutil


# Extend asyncio.create_subprocess_exec with timeout, cwd, and env 
async def subprocess_run(args, timeout=None, stdin=None, stdout=None, stderr=None, **kwargs):
    proc = await asyncio.create_subprocess_exec(*args, stdin=stdin, stdout=stdout, stderr=stderr, **kwargs)

    try:
        stdout, stderr =  await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        if proc.returncode is None:
            try:
                parent = psutil.Process(proc.pid)
                for child in parent.children(recursive=True):
                    try:
                        child.terminate()
                    except:
                        pass
                parent.terminate()
            except:
                pass
        return ("", f'Timeout after {timeout}s'.encode(), -1)

    return (stdout, stderr, proc.returncode)


