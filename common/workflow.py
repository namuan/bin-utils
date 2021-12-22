import logging
import subprocess


def wait_for_enter():
    input("Press Enter to continue: ")


def run_command(command):
    logging.info(f"⚡ {command}")
    return subprocess.check_output(command, shell=True).decode("utf-8")


def __run_step(step, context):
    logging.info(step.__class__.__name__ + " ➡️ " + step.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step.run(context)
    logging.info("-" * 100)


def run_workflow(context: dict, workflow_process: list):
    for step in workflow_process:
        __run_step(step, context)
    logging.info("Done.")
