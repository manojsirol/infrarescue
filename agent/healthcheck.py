import os
import platform
import shutil
import socket
import subprocess
import urllib.error
import urllib.request

import psutil


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

CONTAINER_NAME = os.getenv(
    "INFRARESCUE_CONTAINER_NAME",
    "infrarescue-app"
)

APPLICATION_URL = os.getenv(
    "INFRARESCUE_APPLICATION_URL",
    "http://localhost:8000/health"
)

APPLICATION_PORT = int(
    os.getenv(
        "INFRARESCUE_APPLICATION_PORT",
        "8000"
    )
)

NETWORK_TEST_HOST = os.getenv(
    "INFRARESCUE_NETWORK_TEST_HOST",
    "1.1.1.1"
)

NETWORK_TEST_PORT = int(
    os.getenv(
        "INFRARESCUE_NETWORK_TEST_PORT",
        "443"
    )
)

CPU_WARNING_THRESHOLD = 80
CPU_CRITICAL_THRESHOLD = 90

MEMORY_WARNING_THRESHOLD = 80
MEMORY_CRITICAL_THRESHOLD = 90

DISK_WARNING_THRESHOLD = 80
DISK_CRITICAL_THRESHOLD = 90


# ---------------------------------------------------------
# Host Check
# ---------------------------------------------------------

def check_host():
    """
    Collect basic host information.

    If the InfraRescue agent is executing successfully,
    the underlying operating system is considered reachable.
    """

    try:
        hostname = socket.gethostname()
        operating_system = platform.system()
        release = platform.release()

        return {
            "component": "host",
            "status": "healthy",
            "message": (
                f"{hostname} running "
                f"{operating_system} {release}"
            ),
            "hostname": hostname,
            "os": operating_system,
            "release": release
        }

    except Exception as error:
        return {
            "component": "host",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# CPU Check
# ---------------------------------------------------------

def check_cpu():
    """
    Check current CPU utilization.
    """

    try:
        usage_percent = psutil.cpu_percent(
            interval=1
        )

        if usage_percent >= CPU_CRITICAL_THRESHOLD:
            status = "critical"

        elif usage_percent >= CPU_WARNING_THRESHOLD:
            status = "warning"

        else:
            status = "healthy"

        return {
            "component": "cpu",
            "status": status,
            "message": (
                f"CPU usage: "
                f"{usage_percent:.1f}%"
            ),
            "usage_percent": round(
                usage_percent,
                1
            )
        }

    except Exception as error:
        return {
            "component": "cpu",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Memory Check
# ---------------------------------------------------------

def check_memory():
    """
    Check current system memory utilization.
    """

    try:
        memory = psutil.virtual_memory()

        usage_percent = memory.percent

        if usage_percent >= MEMORY_CRITICAL_THRESHOLD:
            status = "critical"

        elif usage_percent >= MEMORY_WARNING_THRESHOLD:
            status = "warning"

        else:
            status = "healthy"

        return {
            "component": "memory",
            "status": status,
            "message": (
                f"Memory usage: "
                f"{usage_percent:.1f}%"
            ),
            "usage_percent": round(
                usage_percent,
                1
            )
        }

    except Exception as error:
        return {
            "component": "memory",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Network Check
# ---------------------------------------------------------

def check_network():
    """
    Check outbound network connectivity.

    This uses a TCP connection instead of ping so it
    works even when ICMP traffic is blocked.
    """

    try:
        connection = socket.create_connection(
            (
                NETWORK_TEST_HOST,
                NETWORK_TEST_PORT
            ),
            timeout=3
        )

        connection.close()

        return {
            "component": "network",
            "status": "healthy",
            "message": (
                f"Network connectivity available "
                f"via {NETWORK_TEST_HOST}:"
                f"{NETWORK_TEST_PORT}"
            )
        }

    except socket.timeout:
        return {
            "component": "network",
            "status": "down",
            "message": (
                "Network connectivity test "
                "timed out"
            )
        }

    except OSError as error:
        return {
            "component": "network",
            "status": "down",
            "message": (
                f"Network connectivity failed: "
                f"{error}"
            )
        }

    except Exception as error:
        return {
            "component": "network",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# EC2 Environment Check
# ---------------------------------------------------------

def check_ec2():
    """
    Detect whether InfraRescue is running inside AWS EC2.

    Uses the EC2 Instance Metadata Service (IMDSv2).

    This does not create AWS resources and does not require
    AWS access keys.

    When running locally, the check returns not_applicable.
    """

    token_url = (
        "http://169.254.169.254/"
        "latest/api/token"
    )

    instance_id_url = (
        "http://169.254.169.254/"
        "latest/meta-data/instance-id"
    )

    try:
        token_request = urllib.request.Request(
            token_url,
            method="PUT",
            headers={
                "X-aws-ec2-metadata-token-ttl-seconds":
                    "60"
            }
        )

        with urllib.request.urlopen(
            token_request,
            timeout=1
        ) as response:
            token = response.read().decode(
                "utf-8"
            )

        metadata_request = urllib.request.Request(
            instance_id_url,
            headers={
                "X-aws-ec2-metadata-token":
                    token
            }
        )

        with urllib.request.urlopen(
            metadata_request,
            timeout=1
        ) as response:
            instance_id = (
                response
                .read()
                .decode("utf-8")
            )

        return {
            "component": "ec2",
            "status": "healthy",
            "message": (
                f"Running on EC2 instance "
                f"{instance_id}"
            ),
            "instance_id": instance_id
        }

    except (
        urllib.error.URLError,
        TimeoutError,
        OSError
    ):
        return {
            "component": "ec2",
            "status": "not_applicable",
            "message": (
                "Agent is not running inside "
                "an EC2 instance"
            )
        }

    except Exception as error:
        return {
            "component": "ec2",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Docker Check
# ---------------------------------------------------------

def check_docker():
    """
    Check whether Docker is available and responding.

    docker info works with Docker Desktop on Windows
    and Docker Engine on Linux.
    """

    try:
        result = subprocess.run(
            [
                "docker",
                "info"
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return {
                "component": "docker",
                "status": "healthy",
                "message": (
                    "Docker is running and "
                    "responding"
                )
            }

        error_message = (
            result.stderr.strip()
        )

        return {
            "component": "docker",
            "status": "down",
            "message": (
                error_message
                or "Docker is not responding"
            )
        }

    except FileNotFoundError:
        return {
            "component": "docker",
            "status": "down",
            "message": (
                "Docker CLI was not found"
            )
        }

    except subprocess.TimeoutExpired:
        return {
            "component": "docker",
            "status": "down",
            "message": (
                "Docker command timed out"
            )
        }

    except Exception as error:
        return {
            "component": "docker",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Container Check
# ---------------------------------------------------------

def check_container():
    """
    Check whether the monitored application container
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
                "message": (
                    f"{CONTAINER_NAME} "
                    f"does not exist"
                )
            }

        if status == "running":
            return {
                "component": "container",
                "status": "healthy",
                "message": (
                    f"{CONTAINER_NAME} "
                    f"is running"
                )
            }

        return {
            "component": "container",
            "status": "down",
            "message": (
                f"{CONTAINER_NAME} "
                f"status: {status}"
            )
        }

    except FileNotFoundError:
        return {
            "component": "container",
            "status": "unknown",
            "message": (
                "Docker CLI was not found"
            )
        }

    except Exception as error:
        return {
            "component": "container",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Port Check
# ---------------------------------------------------------

def check_port():
    """
    Check whether the monitored application port
    accepts TCP connections.
    """

    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    sock.settimeout(2)

    try:
        result = sock.connect_ex(
            (
                "127.0.0.1",
                APPLICATION_PORT
            )
        )

        if result == 0:
            return {
                "component": "port",
                "status": "healthy",
                "message": (
                    f"Port {APPLICATION_PORT} "
                    f"is listening"
                )
            }

        return {
            "component": "port",
            "status": "down",
            "message": (
                f"Port {APPLICATION_PORT} "
                f"is not listening"
            )
        }

    except Exception as error:
        return {
            "component": "port",
            "status": "unknown",
            "message": str(error)
        }

    finally:
        sock.close()


# ---------------------------------------------------------
# Application Check
# ---------------------------------------------------------

def check_application():
    """
    Check the monitored application's health endpoint.
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
                "message": (
                    f"Health check returned "
                    f"HTTP {status_code}"
                )
            }

        return {
            "component": "application",
            "status": "unhealthy",
            "message": (
                f"Health check returned "
                f"HTTP {status_code}"
            )
        }

    except urllib.error.HTTPError as error:
        return {
            "component": "application",
            "status": "unhealthy",
            "message": (
                f"Application returned "
                f"HTTP {error.code}"
            )
        }

    except urllib.error.URLError as error:
        return {
            "component": "application",
            "status": "down",
            "message": (
                f"Application unreachable: "
                f"{error.reason}"
            )
        }

    except Exception as error:
        return {
            "component": "application",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Disk Check
# ---------------------------------------------------------

def check_disk():
    """
    Check disk utilization.
    """

    try:
        total, used, free = shutil.disk_usage(
            "/"
        )

        usage_percent = (
            used / total
        ) * 100

        if usage_percent >= DISK_CRITICAL_THRESHOLD:
            status = "critical"

        elif usage_percent >= DISK_WARNING_THRESHOLD:
            status = "warning"

        else:
            status = "healthy"

        return {
            "component": "disk",
            "status": status,
            "message": (
                f"Disk usage: "
                f"{usage_percent:.1f}%"
            ),
            "usage_percent": round(
                usage_percent,
                1
            )
        }

    except Exception as error:
        return {
            "component": "disk",
            "status": "unknown",
            "message": str(error)
        }


# ---------------------------------------------------------
# Run All Checks
# ---------------------------------------------------------

def run_all_checks():
    """
    Execute the complete InfraRescue infrastructure
    health-check pipeline.
    """

    results = [
        check_ec2(),
        check_host(),
        check_network(),
        check_cpu(),
        check_memory(),
        check_disk(),
        check_docker(),
        check_container(),
        check_port(),
        check_application()
    ]

    return results


# ---------------------------------------------------------
# Test Mode
# ---------------------------------------------------------

if __name__ == "__main__":

    results = run_all_checks()

    print()
    print(
        "=============================================="
    )
    print(
        "          INFRARESCUE HEALTH CHECK"
    )
    print(
        "=============================================="
    )
    print()

    for result in results:

        print(
            f"[{result['status'].upper():14}] "
            f"{result['component']:12} "
            f"{result['message']}"
        )

    print()

    print(
        "=============================================="
    )