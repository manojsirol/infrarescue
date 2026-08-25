import subprocess
import json
import os
import time
from datetime import datetime


CHECK_INTERVAL = 10

CONTAINER_NAME = "infrarescue-app"

INCIDENT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "incidents",
    "incidents.json"
)


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )

        return result.stdout.strip(), result.stderr.strip()

    except Exception as error:
        return "", str(error)


def check_container():

    output, error = run_command(
        ["docker", "inspect", "-f", "{{.State.Running}}", CONTAINER_NAME]
    )

    if error:
        return False

    return output.lower() == "true"


def load_incidents():

    if not os.path.exists(INCIDENT_FILE):
        return []

    try:
        with open(INCIDENT_FILE, "r") as file:
            data = json.load(file)

            if isinstance(data, list):
                return data

            return []

    except Exception:
        return []


def save_incidents(incidents):

    os.makedirs(os.path.dirname(INCIDENT_FILE), exist_ok=True)

    with open(INCIDENT_FILE, "w") as file:
        json.dump(incidents, file, indent=4)


def create_incident():

    incident = {
        "id": f"INC-{int(time.time())}",
        "service": CONTAINER_NAME,
        "timestamp": get_timestamp(),
        "status": "OPEN",
        "failure_type": "Container Stopped",
        "known_issue": True,
        "message": f"{CONTAINER_NAME} is not running",
        "resolution": None,
        "resolved_at": None
    }

    incidents = load_incidents()

    incidents.insert(0, incident)

    save_incidents(incidents)

    print(f"[INCIDENT CREATED] {incident['id']}")

    return incident


def resolve_incident(incident):

    print("[RECOVERY] Attempting safe recovery...")

    output, error = run_command(
        ["docker", "start", CONTAINER_NAME]
    )

    if error:
        print(f"[RECOVERY ERROR] {error}")

    time.sleep(3)

    is_running = check_container()

    incidents = load_incidents()

    for item in incidents:

        if item["id"] == incident["id"]:

            if is_running:

                item["status"] = "RESOLVED"
                item["resolution"] = "Container restarted successfully"
                item["resolved_at"] = get_timestamp()

                print("[RESOLVED] Container restarted successfully")

            else:

                item["status"] = "ESCALATED"
                item["resolution"] = (
                    "Automatic recovery failed. "
                    "Manual engineer investigation required."
                )

                print("[ESCALATED] Manual investigation required")

            break

    save_incidents(incidents)


def has_open_incident():

    incidents = load_incidents()

    for incident in incidents:

        if (
            incident["service"] == CONTAINER_NAME
            and incident["status"] == "OPEN"
        ):
            return True

    return False


def monitor():

    print("==========================================")
    print("       InfraRescue Monitoring Agent")
    print("==========================================")
    print(f"Monitoring: {CONTAINER_NAME}")
    print(f"Check interval: {CHECK_INTERVAL} seconds")
    print("Press CTRL + C to stop monitoring")
    print("==========================================")

    while True:

        try:

            print(f"\n[{get_timestamp()}] Checking infrastructure...")

            is_running = check_container()

            if is_running:

                print(f"[HEALTHY] {CONTAINER_NAME} is running")

            else:

                print(f"[DOWN] {CONTAINER_NAME} is NOT running")

                if has_open_incident():

                    print(
                        "[INFO] Incident already exists. "
                        "Waiting for recovery result."
                    )

                else:

                    print("[DIAGNOSIS] Checking known failure patterns...")

                    print(
                        "[KNOWN ISSUE] Container stopped"
                    )

                    incident = create_incident()

                    resolve_incident(incident)

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:

            print("\nMonitoring stopped by user.")

            break

        except Exception as error:

            print(f"[AGENT ERROR] {error}")

            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    monitor()