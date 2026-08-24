import docker
import json
import os
import time
from datetime import datetime


# Connect to Docker
client = docker.from_env()


# Project base directory
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


# Incident file location
INCIDENT_FILE = os.path.join(
    BASE_DIR,
    "incidents",
    "incidents.json"
)


# Container to monitor
CONTAINER_NAME = "infrarescue-app"


def load_incidents():

    if not os.path.exists(INCIDENT_FILE):
        return []

    try:
        with open(INCIDENT_FILE, "r") as file:
            return json.load(file)

    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_incidents(incidents):

    with open(INCIDENT_FILE, "w") as file:
        json.dump(
            incidents,
            file,
            indent=4
        )


def get_container():

    try:

        container = client.containers.get(
            CONTAINER_NAME
        )

        return container

    except docker.errors.NotFound:

        return None


def create_incident(problem, classification):

    incidents = load_incidents()


    incident = {

        "id": f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",

        "service": CONTAINER_NAME,

        "detected_at":
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "problem": problem,

        "classification": classification,

        "action": "Diagnosis in progress",

        "status": "Open",

        "resolved_at": None

    }


    incidents.append(incident)

    save_incidents(incidents)

    return incident


def update_incident(
    incident_id,
    status,
    action,
    resolved_at=None
):

    incidents = load_incidents()


    for incident in incidents:

        if incident["id"] == incident_id:

            incident["status"] = status

            incident["action"] = action

            if resolved_at:

                incident["resolved_at"] = resolved_at


    save_incidents(incidents)


def verify_application_health():

    container = get_container()


    if container is None:

        return False


    container.reload()


    if container.status != "running":

        return False


    return True


def safe_recovery(incident):

    print("\n" + "=" * 50)

    print("SAFE AUTO-RECOVERY STARTED")

    print("=" * 50)


    print("\n[RECOVERY 1/3] Attempting container restart...")


    try:

        container = get_container()


        if container is None:

            print("Container not found.")

            return False


        container.start()


        print(
            f"✓ Restart command sent to "
            f"{CONTAINER_NAME}"
        )


    except Exception as error:

        print(
            f"✗ Recovery failed: {error}"
        )

        return False


    print(
        "\n[RECOVERY 2/3] Waiting for "
        "application to start..."
    )


    time.sleep(3)


    print(
        "\n[RECOVERY 3/3] Verifying "
        "application health..."
    )


    if verify_application_health():

        print(
            "✓ Container is running after "
            "recovery"
        )


        update_incident(

            incident["id"],

            "Resolved",

            "Container automatically restarted "
            "and health check passed",

            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        print(
            "\n✓ INCIDENT RESOLVED "
            "AUTOMATICALLY"
        )


        return True


    else:

        print(
            "✗ Application recovery verification "
            "failed"
        )


        update_incident(

            incident["id"],

            "Escalated",

            "Automatic recovery failed. "
            "Manual engineer investigation required."
        )


        return False


def monitor_container():

    print("\n" + "=" * 55)

    print("INFRARESCUE - INFRASTRUCTURE CHECK")

    print("=" * 55)


    # STEP 1

    print(
        "\n[1/4] Checking Docker Engine..."
    )


    try:

        client.ping()

        print(
            "✓ Docker Engine is running"
        )


    except Exception as error:

        print(
            "✗ Docker Engine is NOT reachable"
        )


        incident = create_incident(

            "Docker Engine is not reachable",

            "Unknown Incident"
        )


        update_incident(

            incident["id"],

            "Escalated",

            "Manual investigation required"
        )


        return


    # STEP 2

    print(
        "\n[2/4] Checking application "
        "container..."
    )


    container = get_container()


    if container is None:

        print(
            "✗ Application container "
            "not found"
        )


        incident = create_incident(

            "Application container not found",

            "Unknown Incident"
        )


        update_incident(

            incident["id"],

            "Escalated",

            "Manual investigation required"
        )


        return


    container.reload()


    print(
        f"Container status: "
        f"{container.status}"
    )


    # STEP 3

    print(
        "\n[3/4] Diagnosing application "
        "status..."
    )


    if container.status == "running":

        print(
            "✓ Application container "
            "is running"
        )


        print(
            "\n[4/4] Infrastructure check "
            "completed"
        )


        print(
            "\nRESULT: ALL SYSTEMS "
            "OPERATIONAL"
        )


        return


    elif container.status == "exited":

        print(
            "✗ Application container "
            "is STOPPED"
        )


        print("\nDiagnosis:")

        print(
            "Docker Engine: RUNNING"
        )

        print(
            "Application Container: STOPPED"
        )


        print(
            "\nClassification: "
            "KNOWN INCIDENT"
        )


        print(
            "Recovery Runbook: "
            "Restart Application Container"
        )


        incident = create_incident(

            "Application container stopped",

            "Known Incident"
        )


        # STEP 4

        print(
            "\n[4/4] Starting safe recovery..."
        )


        safe_recovery(incident)


    else:

        print(
            f"✗ Unexpected container "
            f"status: {container.status}"
        )


        incident = create_incident(

            f"Unexpected container status: "
            f"{container.status}",

            "Unknown Incident"
        )


        update_incident(

            incident["id"],

            "Escalated",

            "Unknown problem. "
            "Manual engineer investigation required."
        )


if __name__ == "__main__":

    monitor_container()