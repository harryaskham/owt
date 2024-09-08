import subprocess
def run(cmd: str) -> bytes:
    out = subprocess.run(["bash", "-c", cmd], stdout=subprocess.PIPE)
    return out.stdout
