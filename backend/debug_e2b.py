import sys

log = open("e2b_debug_output.txt", "w")

try:
    import e2b_code_interpreter
    log.write(f"Module: {e2b_code_interpreter}\n")
    log.write(f"Dir: {dir(e2b_code_interpreter)}\n")
    
    try:
        from e2b_code_interpreter import Sandbox
        log.write("Sandbox: FOUND\n")
    except ImportError:
        log.write("Sandbox: NOT FOUND\n")

    try:
        from e2b_code_interpreter import CodeInterpreter
        log.write("CodeInterpreter: FOUND\n")
    except ImportError:
        log.write("CodeInterpreter: NOT FOUND\n")

except ImportError as e:
    log.write(f"ImportError: {e}\n")

log.close()
