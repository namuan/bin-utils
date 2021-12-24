import logging
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()


def notify_me(msg):
    pushover_url = os.getenv("PUSHOVER_URL")
    pushover_token = os.getenv("PUSHOVER_TOKEN")
    pushover_user = os.getenv("PUSHOVER_USER")
    if pushover_url and pushover_token and pushover_user:
        run_command(
            f"curl -s -F 'token={pushover_token}' -F 'user={pushover_user}' -F 'message={msg}' {pushover_url}"
        )


def wait_for_enter():
    input("Press Enter to continue: ")


def run_command(command):
    logging.info(f"⚡ {command}")
    return subprocess.check_output(command, shell=True).decode("utf-8")


def __run_step(step, context):
    step_instance = step(context, step)
    logging.info(step.__name__ + " ➡️ " + step_instance.__doc__)
    if context.get("verbose"):
        logging.info(context)
    step_instance.run(context)
    logging.info("-" * 100)


def run_workflow(context: dict, workflow_process: list):
    for step in workflow_process:
        __run_step(step, context)
    logging.info("Done.")


class WorkflowBase:
    def __init__(self, context, step):
        maybe_vars = vars(step).get("__annotations__")
        if maybe_vars:
            step_vars = maybe_vars.keys()
            try:
                for step_var in step_vars:
                    setattr(self, step_var, context[step_var])
            except KeyError as e:
                logging.error(
                    "Unable to find variable: %s  in workflow class: %s",
                    str(e),
                    step.__name__,
                )
                logging.info("Available keys in context: %s", context.keys())
                raise e
