def run(cmd: str) -> bytes:
    import subprocess

    out = subprocess.run(["bash", "-c", cmd], stdout=subprocess.PIPE)
    return out.stdout
