import random
import string
from pathlib import Path
import shutil


def create_dir(output_dir):
    path = Path(output_dir)
    if path.exists():
        shutil.rmtree(output_dir)

    path.mkdir()


def random_string(length):
    return "".join(
        random.choice(string.ascii_uppercase + string.digits) for _ in range(length)
    )


def job_hash(job):
    return random_string(len(job.get("q")))
