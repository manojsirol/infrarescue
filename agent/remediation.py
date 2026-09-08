import subprocess
import time


CONTAINER_NAME = "infrarescue-app"


def run_command(command):
    """
    Execute a predefined system command safely.
    """

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=15
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip()
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "Command timed out"
        }

    except Exception as error:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(error)
        }


def check_container_running():
    """
    Verify whether the application container is running.
    """

    result = run_command(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            CONTAINER_NAME
        ]
    )

    if not result["success"]:
        return False

    return result["stdout"].lower() == "true"


def restart_container():
    """
    Attempt a safe restart of the application container
    and verify that it is running afterward.
    """

    print("[REMEDIATION] Restarting application container...")

    result = run_command(
        [
            "docker",
            "start",
            CONTAINER_NAME
        ]
    )

    if not result["success"]:
        return {
            "success": False,
            "action": "RESTART_CONTAINER",
            "message": result["stderr"] or "Container restart failed"
        }

    time.sleep(3)

    if check_container_running():
        return {
            "success": True,
            "action": "RESTART_CONTAINER",
            "message": "Container restarted successfully"
        }

    return {
        "success": False,
        "action": "RESTART_CONTAINER",
        "message": "Container restart command completed but verification failed"
    }


def execute_remediation(diagnosis):
    """
    Execute only explicitly approved remediation actions.

    Unknown or unsafe actions are never executed automatically.
    """

    action = diagnosis.get("recommended_action")

    if action == "RESTART_CONTAINER":
        return restart_container()

    if action == "ESCALATE":
        return {
            "success": False,
            "action": "ESCALATE",
            "message": (
                "No safe automatic remediation is available. "
                "Engineer investigation required."
            )
        }

    return {
        "success": False,
        "action": action or "NONE",
        "message": "No remediation action configured"
    }