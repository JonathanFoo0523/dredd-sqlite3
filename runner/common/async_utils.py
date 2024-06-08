import asyncio
import psutil
import subprocess
import os
import signal

TIMEOUT_RETCODE = 124   # Same as UNIX tiemout return code


# Extend asyncio.create_subprocess_exec with timeout, so it function similarly as subprocess.run()
async def subprocess_run(args, timeout=None, stdin=None, input=None, stdout=None, stderr=None, **kwargs):
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True, **kwargs)
        stdout, stderr =  await asyncio.wait_for(proc.communicate(input), timeout=timeout)
    except KeyboardInterrupt:
        pass
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
        if proc is not None and proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except:
                pass
            # proc.terminate()
        
        if proc and proc.stdin:
            try:
                await proc.stdin.wait_closed()
            except BrokenPipeError:
                pass


    return (stdout, stderr, proc.returncode)


READSIZE = 1024 * 1024 * 1024
MAX_BUFSIZE = 1024 * 1024 * 1024 * 10 # 10GB

class MaxBufferSizeExceeded(Exception):
    pass

async def read(stdpipe):
    result = bytearray()
    while True:
        buf = await stdpipe.read(READSIZE)
        if not buf:
            break
        
        result.extend(buf)
        if len(result) > MAX_BUFSIZE:
            raise MaxBufferSizeExceeded(f"Buffersize exceed {MAX_BUFSIZE} bytes")
    return result


async def write_stdin(stdin, input):
    stdin.write(input)
    await stdin.drain()
    stdin.close()

async def do_notihng():
    return None

# Instead of using communicate, which is prone to OOM when stdout is PIPE and output is large, this method
# write to buffer and check if buff is larger than certain size
async def subprocess_run_safe(args, timeout=None, stdin=None, input=None, stdout=None, stderr=None, **kwargs):
    proc = None

    try:
        proc = await asyncio.create_subprocess_exec(*args, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True, **kwargs)

        tasks = [
            read(proc.stdout) if stdout == asyncio.subprocess.PIPE else do_notihng(),
            read(proc.stderr) if stderr == asyncio.subprocess.PIPE else do_notihng(),
            write_stdin(proc.stdin, input) if stdin == asyncio.subprocess.PIPE else do_notihng()
        ]

        async with asyncio.timeout(timeout):
            stdout, stderr, _ = await asyncio.gather(*tasks)

    except KeyboardInterrupt:
        pass
    # except asyncio.TimeoutError:
    #     return ("", f'Timeout after {timeout}s'.encode(), TIMEOUT_RETCODE)
    finally:
        if proc is not None and proc.returncode is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except:
                pass
        
        if proc and proc.stdin:
            try:
                await proc.stdin.wait_closed()
            except BrokenPipeError:
                pass

    return (stdout, stderr, proc.returncode)