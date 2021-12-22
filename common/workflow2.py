import logging
import subprocess

import dacite


def wait_for_enter():
    input("Press Enter to continue: ")


def run_command(command):
    logging.info(f"⚡ {command}")
    return subprocess.check_output(command, shell=True).decode("utf-8")


def __run_step(step, context):
    step_instance = step(context, step.Input)
    logging.info(step.__name__ + " ➡️ " + step_instance.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step_instance.run(context)
    logging.info("-" * 100)


def run_workflow2(context: dict, workflow_process: list):
    for step in workflow_process:
        __run_step(step, context)
    logging.info("Done.")


class WorkflowBase:
    def __init__(self, context, input_clazz):
        self.input = dacite.from_dict(data_class=input_clazz, data=context)
