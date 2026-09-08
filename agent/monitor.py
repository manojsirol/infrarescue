import json
import os
import time
from datetime import datetime

from healthcheck import run_all_checks
from diagnosis import diagnose
from remediation import execute_remediation


CHECK_INTERVAL = 10

CONTAINER_NAME = "infrarescue-app"

INCIDENT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "incidents",
    "incidents.json"
)


def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_failed_checks():
    """
    Run all infrastructure health checks
    and return the complete results plus failures.
    """

    results = run_all_checks()

    failures = []

    for result in results:
        if result["status"] in [
            "down",
            "critical",
            "unhealthy"
        ]:
            failures.append(result)

    return results, failures


def load_incidents():
    """
    Load incidents from the local incidents JSON file.
    """

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
    """
    Save incidents to the local incidents JSON file.
    """

    os.makedirs(
        os.path.dirname(INCIDENT_FILE),
        exist_ok=True
    )

    with open(INCIDENT_FILE, "w") as file:
        json.dump(
            incidents,
            file,
            indent=4
        )


def create_incident(diagnosis_result):
    """
    Create a new incident using the diagnosis result.
    """

    incident = {
        "id": f"INC-{int(time.time())}",
        "service": CONTAINER_NAME,
        "timestamp": get_timestamp(),
        "status": "OPEN",

        "root_cause": diagnosis_result["root_cause"],
        "known_issue": diagnosis_result["known_issue"],
        "severity": diagnosis_result["severity"],
        "confidence": diagnosis_result["confidence"],
        "recommended_action": diagnosis_result[
            "recommended_action"
        ],

        "message": diagnosis_result["message"],
        "dependent_symptoms": diagnosis_result[
            "dependent_symptoms"
        ],

        "resolution": None,
        "resolved_at": None
    }

    incidents = load_incidents()

    incidents.insert(0, incident)

    save_incidents(incidents)

    print(
        f"[INCIDENT CREATED] "
        f"{incident['id']}"
    )

    return incident


def has_open_incident(root_cause):
    """
    Check whether an active incident already exists
    for the same service and root cause.

    This prevents duplicate incidents for the same
    ongoing failure.
    """

    incidents = load_incidents()

    active_statuses = [
        "OPEN",
        "ESCALATED"
    ]

    for incident in incidents:

        if (
            incident.get("service") == CONTAINER_NAME
            and incident.get("root_cause") == root_cause
            and incident.get("status") in active_statuses
        ):
            return True

    return False


def update_incident_after_remediation(
    incident,
    remediation_result
):
    """
    Update an incident using the remediation result.
    """

    incidents = load_incidents()

    for item in incidents:

        if item.get("id") != incident["id"]:
            continue

        if remediation_result["success"]:

            item["status"] = "RESOLVED"

            item["resolution"] = remediation_result[
                "message"
            ]

            item["resolved_at"] = get_timestamp()

            print(
                f"[RESOLVED] "
                f"{remediation_result['message']}"
            )

        else:

            if (
                remediation_result["action"]
                == "ESCALATE"
            ):

                item["status"] = "ESCALATED"

                print(
                    f"[ESCALATED] "
                    f"{remediation_result['message']}"
                )

            else:

                item["status"] = "FAILED"

                print(
                    f"[REMEDIATION FAILED] "
                    f"{remediation_result['message']}"
                )

            item["resolution"] = remediation_result[
                "message"
            ]

        break

    save_incidents(incidents)


def print_diagnosis(diagnosis_result):
    """
    Display the diagnosis result clearly.
    """

    print(
        f"[ROOT CAUSE] "
        f"{diagnosis_result['root_cause']}"
    )

    print(
        f"[SEVERITY] "
        f"{diagnosis_result['severity']}"
    )

    print(
        f"[CONFIDENCE] "
        f"{diagnosis_result['confidence']}"
    )

    if diagnosis_result["known_issue"]:
        print("[KNOWN ISSUE] YES")
    else:
        print("[KNOWN ISSUE] NO")

    print(
        f"[RECOMMENDED ACTION] "
        f"{diagnosis_result['recommended_action']}"
    )

    if diagnosis_result["dependent_symptoms"]:

        print("[DEPENDENT SYMPTOMS]")

        for symptom in diagnosis_result[
            "dependent_symptoms"
        ]:

            print(
                f"    - {symptom}"
            )


def monitor():
    """
    Main InfraRescue monitoring loop.
    """

    print("==========================================")
    print("       InfraRescue Monitoring Agent")
    print("==========================================")
    print(f"Monitoring: {CONTAINER_NAME}")
    print(
        f"Check interval: "
        f"{CHECK_INTERVAL} seconds"
    )
    print("Press CTRL + C to stop monitoring")
    print("==========================================")

    while True:

        try:

            print(
                f"\n[{get_timestamp()}] "
                f"Checking infrastructure..."
            )

            results, failures = get_failed_checks()

            if not failures:

                print(
                    "[HEALTHY] "
                    "All infrastructure checks passed"
                )

            else:

                print(
                    f"[FAILURE] "
                    f"{len(failures)} infrastructure "
                    f"check(s) failed"
                )

                for failure in failures:

                    print(
                        f"    "
                        f"[{failure['status'].upper()}] "
                        f"{failure['component']}: "
                        f"{failure['message']}"
                    )

                # -------------------------------------
                # Diagnosis
                # -------------------------------------

                print(
                    "[DIAGNOSIS] "
                    "Analyzing infrastructure state..."
                )

                diagnosis_result = diagnose(results)

                print_diagnosis(
                    diagnosis_result
                )

                # -------------------------------------
                # Duplicate incident protection
                # -------------------------------------

                if has_open_incident(
                    diagnosis_result["root_cause"]
                ):

                    print(
                        "[INFO] Matching active incident "
                        "already exists. "
                        "Waiting for recovery result."
                    )

                else:

                    # ---------------------------------
                    # Incident creation
                    # ---------------------------------

                    incident = create_incident(
                        diagnosis_result
                    )

                    # ---------------------------------
                    # Safe remediation
                    # ---------------------------------

                    remediation_result = (
                        execute_remediation(
                            diagnosis_result
                        )
                    )

                    # ---------------------------------
                    # Incident update
                    # ---------------------------------

                    update_incident_after_remediation(
                        incident,
                        remediation_result
                    )

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print(
                "\nMonitoring stopped by user."
            )

            break

        except Exception as error:

            print(
                f"[AGENT ERROR] {error}"
            )

            time.sleep(
                CHECK_INTERVAL
            )


if __name__ == "__main__":
    monitor()