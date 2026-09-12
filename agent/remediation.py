import os
import platform
import socket
import subprocess
import time
import urllib.error
import urllib.request


CONTAINER_NAME = "infrarescue-app"
APPLICATION_PORT = 8000
APPLICATION_URL = "http://localhost:8000/health"

ANSIBLE_PLAYBOOK = "/usr/local/bin/ansible-playbook"
DOCKER_RECOVERY_RUNBOOK = "/opt/infrarescue/runbooks/start_docker.yml"


def run_command(command, timeout=15):
    """
    Execute a predefined system command safely.
    """

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout
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


def check_application_port():
    """
    Verify whether the application port is accepting TCP connections.
    """

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.settimeout(2)

    try:
        result = sock.connect_ex(
            ("127.0.0.1", APPLICATION_PORT)
        )

        return result == 0

    except Exception:
        return False

    finally:
        sock.close()


def check_application_health():
    """
    Verify whether the application health endpoint returns HTTP 200.
    """

    try:
        response = urllib.request.urlopen(
            APPLICATION_URL,
            timeout=5
        )

        return response.status == 200

    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError
    ):
        return False

    except Exception:
        return False


def check_docker_service():
    """
    Verify whether the Docker engine is responding.
    """

    result = run_command(
        [
            "docker",
            "info"
        ]
    )

    return result["success"]


def verify_recovery():
    """
    Perform full post-remediation verification.

    Recovery is considered successful only if:

    1. Container is running
    2. Port 8000 is reachable
    3. /health returns HTTP 200
    """

    print("[VERIFY] Checking container state...")

    if not check_container_running():
        return {
            "success": False,
            "message": "Container is not running after remediation"
        }

    print("[VERIFY] Container is running")

    print("[VERIFY] Checking application port...")

    if not check_application_port():
        return {
            "success": False,
            "message": (
                f"Container is running but port "
                f"{APPLICATION_PORT} is unavailable"
            )
        }

    print(
        f"[VERIFY] Port "
        f"{APPLICATION_PORT} is reachable"
    )

    print("[VERIFY] Checking application health endpoint...")

    if not check_application_health():
        return {
            "success": False,
            "message": (
                "Container and port are available "
                "but application health check failed"
            )
        }

    print("[VERIFY] Application health check passed")

    return {
        "success": True,
        "message": (
            "Container, application port and health "
            "endpoint verified successfully"
        )
    }


def restart_container():
    """
    Restart the application container and perform
    full post-remediation verification.
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
            "message": (
                result["stderr"]
                or "Container restart failed"
            )
        }

    print("[REMEDIATION] Container start command completed")

    time.sleep(3)

    verification = verify_recovery()

    if verification["success"]:
        return {
            "success": True,
            "action": "RESTART_CONTAINER",
            "message": verification["message"]
        }

    return {
        "success": False,
        "action": "RESTART_CONTAINER",
        "message": verification["message"]
    }


def start_docker_service():
    """
    Recover the Docker service using the approved
    local Ansible recovery runbook on Linux/EC2.
    """

    operating_system = platform.system()

    if operating_system == "Windows":
        return {
            "success": False,
            "action": "ESCALATE",
            "message": (
                "Docker is unavailable. Automatic Docker service "
                "recovery is not supported in the local Windows "
                "Docker Desktop environment. Engineer intervention "
                "is required."
            )
        }

    if not os.path.isfile(ANSIBLE_PLAYBOOK):
        return {
            "success": False,
            "action": "START_DOCKER",
            "message": (
                "Ansible executable was not found at "
                f"{ANSIBLE_PLAYBOOK}"
            )
        }

    if not os.path.isfile(DOCKER_RECOVERY_RUNBOOK):
        return {
            "success": False,
            "action": "START_DOCKER",
            "message": (
                "Docker recovery runbook was not found at "
                f"{DOCKER_RECOVERY_RUNBOOK}"
            )
        }

    print(
        "[REMEDIATION] Executing approved Ansible "
        "Docker recovery runbook..."
    )

    result = run_command(
        [
            ANSIBLE_PLAYBOOK,
            "-i",
            "localhost,",
            "-c",
            "local",
            DOCKER_RECOVERY_RUNBOOK
        ],
        timeout=60
    )

    if not result["success"]:
        return {
            "success": False,
            "action": "START_DOCKER",
            "message": (
                result["stderr"]
                or result["stdout"]
                or "Docker recovery playbook failed"
            )
        }

    print("[REMEDIATION] Ansible recovery runbook completed")

    time.sleep(2)

    print("[VERIFY] Checking Docker engine...")

    if not check_docker_service():
        return {
            "success": False,
            "action": "START_DOCKER",
            "message": (
                "Ansible recovery completed but Docker "
                "is still unavailable"
            )
        }

    print("[VERIFY] Docker engine is responding")

    return {
        "success": True,
        "action": "START_DOCKER",
        "message": (
            "Docker service was recovered and verified successfully"
        )
    }


def execute_remediation(diagnosis):
    """
    Execute only approved remediation actions based
    on the diagnosis produced by the diagnosis engine.
    """

    if not isinstance(diagnosis, dict):
        return {
            "success": False,
            "action": "ESCALATE",
            "message": "Invalid diagnosis data received"
        }

    if not diagnosis.get("known_issue"):
        return {
            "success": False,
            "action": "ESCALATE",
            "message": (
                "Unknown infrastructure failure. "
                "Automatic remediation is not permitted."
            )
        }

    action = diagnosis.get("recommended_action")

    if action == "RESTART_CONTAINER":
        return restart_container()

    if action == "START_DOCKER":
        return start_docker_service()

    return {
        "success": False,
        "action": "ESCALATE",
        "message": (
            f"No approved remediation exists for action: {action}"
        )
    }
