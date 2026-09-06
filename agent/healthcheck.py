import subprocess
import socket
import urllib.request
import urllib.error
import shutil


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

CONTAINER_NAME = "infrarescue-app"
APPLICATION_URL = "http://localhost:8000/health"
APPLICATION_PORT = 8000


# ---------------------------------------------------------
# Docker Check
# ---------------------------------------------------------

def check_docker():
    """
    Check whether Docker is available and responding.

    We use 'docker info' instead of 'systemctl'
    so this works with Docker Desktop on Windows
    and Docker Engine on Linux.
    """

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return {
                "component": "docker",
                "status": "healthy",
                "message": "Docker is running and responding"
            }

        error_message = result.stderr.strip()

        return {
            "component": "docker",
            "status": "down",
            "message": error_message or "Docker is not responding"
        }

    except FileNotFoundError:
        return {
            "component": "docker",
            "status": "down",
            "message": "Docker CLI was not found"
        }

    except subprocess.TimeoutExpired:
        return {
            "component": "docker",
            "status": "down",
            "message": "Docker command timed out"
        }

    except Exception as e:
        return {
            "component": "docker",
            "status": "unknown",
            "message": str(e)
        }


# ---------------------------------------------------------
# Container Check
# ---------------------------------------------------------

def check_container():
    """
    Check whether the InfraRescue application container
    exists and determine its current state.
    """

    try:
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Status}}",
                CONTAINER_NAME
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        status = result.stdout.strip()

        if result.returncode != 0:
            return {
                "component": "container",
                "status": "down",
                "message": f"{CONTAINER_NAME} does not exist"
            }

        if status == "running":
            return {
                "component": "container",
                "status": "healthy",
                "message": f"{CONTAINER_NAME} is running"
            }

        return {
            "component": "container",
            "status": "down",
            "message": f"{CONTAINER_NAME} status: {status}"
        }

    except FileNotFoundError:
        return {
            "component": "container",
            "status": "unknown",
            "message": "Docker CLI was not found"
        }

    except Exception as e:
        return {
            "component": "container",
            "status": "unknown",
            "message": str(e)
        }


# ---------------------------------------------------------
# Port Check
# ---------------------------------------------------------

def check_port():
    """
    Check whether the application port is accepting
    TCP connections.
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

        if result == 0:
            return {
                "component": "port",
                "status": "healthy",
                "message": f"Port {APPLICATION_PORT} is listening"
            }

        return {
            "component": "port",
            "status": "down",
            "message": f"Port {APPLICATION_PORT} is not listening"
        }

    except Exception as e:
        return {
            "component": "port",
            "status": "unknown",
            "message": str(e)
        }

    finally:
        sock.close()


# ---------------------------------------------------------
# Application Check
# ---------------------------------------------------------

def check_application():
    """
    Check the Flask application's /health endpoint.
    """

    try:
        response = urllib.request.urlopen(
            APPLICATION_URL,
            timeout=5
        )

        status_code = response.status

        if status_code == 200:
            return {
                "component": "application",
                "status": "healthy",
                "message": f"Health check returned HTTP {status_code}"
            }

        return {
            "component": "application",
            "status": "unhealthy",
            "message": f"Health check returned HTTP {status_code}"
        }

    except urllib.error.HTTPError as e:
        return {
            "component": "application",
            "status": "unhealthy",
            "message": f"Application returned HTTP {e.code}"
        }

    except urllib.error.URLError as e:
        return {
            "component": "application",
            "status": "down",
            "message": f"Application unreachable: {e.reason}"
        }

    except Exception as e:
        return {
            "component": "application",
            "status": "unknown",
            "message": str(e)
        }


# ---------------------------------------------------------
# Disk Check
# ---------------------------------------------------------

def check_disk():
    """
    Check disk usage of the current system.
    """

    try:
        total, used, free = shutil.disk_usage("/")

        usage_percent = (used / total) * 100

        if usage_percent >= 90:
            status = "critical"

        elif usage_percent >= 80:
            status = "warning"

        else:
            status = "healthy"

        return {
            "component": "disk",
            "status": status,
            "message": f"Disk usage: {usage_percent:.1f}%",
            "usage_percent": round(usage_percent, 1)
        }

    except Exception as e:
        return {
            "component": "disk",
            "status": "unknown",
            "message": str(e)
        }


# ---------------------------------------------------------
# Run All Checks
# ---------------------------------------------------------

def run_all_checks():
    """
    Execute all InfraRescue health checks.
    """

    results = [
        check_docker(),
        check_container(),
        check_port(),
        check_application(),
        check_disk()
    ]

    return results


# ---------------------------------------------------------
# Test Mode
# ---------------------------------------------------------

if __name__ == "__main__":

    results = run_all_checks()

    print()
    print("==============================================")
    print("          INFRARESCUE HEALTH CHECK")
    print("==============================================")
    print()

    for result in results:

        print(
            f"[{result['status'].upper():9}] "
            f"{result['component']:12} "
            f"{result['message']}"
        )

    print()
    print("==============================================")