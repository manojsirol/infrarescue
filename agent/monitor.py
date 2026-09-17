import json
import os
import time
import uuid
from datetime import datetime

from healthcheck import run_all_checks
from diagnosis import diagnose
from remediation import execute_remediation
from escalation import send_escalation_alert


# =========================================================
# Configuration
# =========================================================

CHECK_INTERVAL = 10

CONTAINER_NAME = os.getenv(
    "INFRARESCUE_CONTAINER_NAME",
    "infrarescue-app"
)

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

INCIDENT_FILE = os.path.join(
    BASE_DIR,
    "incidents",
    "incidents.json"
)

HEALTH_FILE = os.path.join(
    BASE_DIR,
    "runtime",
    "current_health.json"
)


# =========================================================
# General Helpers
# =========================================================

def get_timestamp():
    """
    Return the current local timestamp.
    """

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def generate_incident_id():
    """
    Generate a unique and readable incident ID.

    Example:
    INC-20260918-001355-A91F2C
    """

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    unique_suffix = (
        uuid.uuid4()
        .hex[:6]
        .upper()
    )

    return (
        f"INC-{timestamp}-"
        f"{unique_suffix}"
    )


# =========================================================
# Live Health State
# =========================================================

def determine_overall_health(results):
    """
    Determine overall infrastructure health from
    all component health-check results.
    """

    statuses = {
        result.get(
            "status",
            "unknown"
        )
        for result in results
    }

    if statuses.intersection(
        {
            "down",
            "critical",
            "unhealthy"
        }
    ):
        return "critical"

    if "warning" in statuses:
        return "warning"

    if "unknown" in statuses:
        return "unknown"

    return "healthy"


def save_health_snapshot(results):
    """
    Save the latest live infrastructure state.

    The dashboard reads this snapshot instead of
    trying to determine current health from old
    incident history.
    """

    overall_status = determine_overall_health(
        results
    )

    healthy_count = sum(
        1
        for result in results
        if result.get("status")
        == "healthy"
    )

    warning_count = sum(
        1
        for result in results
        if result.get("status")
        == "warning"
    )

    critical_count = sum(
        1
        for result in results
        if result.get("status") in {
            "down",
            "critical",
            "unhealthy"
        }
    )

    not_applicable_count = sum(
        1
        for result in results
        if result.get("status")
        == "not_applicable"
    )

    unknown_count = sum(
        1
        for result in results
        if result.get("status")
        == "unknown"
    )

    snapshot = {
        "timestamp": get_timestamp(),
        "overall_status": overall_status,

        "summary": {
            "total_components": len(results),
            "healthy": healthy_count,
            "warning": warning_count,
            "critical": critical_count,
            "not_applicable": not_applicable_count,
            "unknown": unknown_count
        },

        "components": results
    }

    os.makedirs(
        os.path.dirname(HEALTH_FILE),
        exist_ok=True
    )

    temporary_file = (
        HEALTH_FILE + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            snapshot,
            file,
            indent=4
        )

    os.replace(
        temporary_file,
        HEALTH_FILE
    )


# =========================================================
# Health Checks
# =========================================================

def get_failed_checks():
    """
    Run all infrastructure health checks.

    Returns:
    - complete health results
    - critical/down/unhealthy results

    Warning states are recorded in the dashboard
    but are not considered outages.
    """

    results = run_all_checks()

    failures = []

    for result in results:

        if result.get("status") in [
            "down",
            "critical",
            "unhealthy"
        ]:

            failures.append(
                result
            )

    return (
        results,
        failures
    )


# =========================================================
# Incident Storage
# =========================================================

def load_incidents():
    """
    Load incident history safely.
    """

    if not os.path.exists(
        INCIDENT_FILE
    ):
        return []

    try:

        with open(
            INCIDENT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

            if isinstance(
                data,
                list
            ):
                return data

            return []

    except (
        json.JSONDecodeError,
        FileNotFoundError,
        OSError
    ):
        return []


def save_incidents(incidents):
    """
    Save incident history safely.

    A temporary file is used so the dashboard
    does not read partially written JSON.
    """

    os.makedirs(
        os.path.dirname(
            INCIDENT_FILE
        ),
        exist_ok=True
    )

    temporary_file = (
        INCIDENT_FILE + ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            incidents,
            file,
            indent=4
        )

    os.replace(
        temporary_file,
        INCIDENT_FILE
    )


# =========================================================
# Incident Ownership
# =========================================================

def get_incident_service(
    diagnosis_result
):
    """
    Determine which infrastructure component
    owns an incident.
    """

    root_cause = diagnosis_result.get(
        "root_cause",
        ""
    )

    if root_cause.startswith(
        "DISK_"
    ):
        return "host-disk"

    if root_cause.startswith(
        "MEMORY_"
    ):
        return "host-memory"

    if root_cause.startswith(
        "CPU_"
    ):
        return "host-cpu"

    if root_cause.startswith(
        "NETWORK_"
    ):
        return "network"

    if root_cause.startswith(
        "DOCKER_"
    ):
        return "docker"

    if root_cause.startswith(
        "EC2_"
    ):
        return "ec2"

    if root_cause.startswith(
        "HOST_"
    ):
        return "host"

    return CONTAINER_NAME


# =========================================================
# Incident Creation
# =========================================================

def create_incident(
    diagnosis_result,
    service=None
):
    """
    Create a new incident from a diagnosis.
    """

    incident_service = (
        service
        or get_incident_service(
            diagnosis_result
        )
    )

    incident = {
        "id": generate_incident_id(),

        "service": incident_service,

        "timestamp": get_timestamp(),

        "status": "OPEN",

        "root_cause":
            diagnosis_result.get(
                "root_cause",
                "UNKNOWN_FAILURE"
            ),

        "known_issue":
            diagnosis_result.get(
                "known_issue",
                False
            ),

        "severity":
            diagnosis_result.get(
                "severity",
                "UNKNOWN"
            ),

        "confidence":
            diagnosis_result.get(
                "confidence",
                "UNKNOWN"
            ),

        "recommended_action":
            diagnosis_result.get(
                "recommended_action",
                "ESCALATE"
            ),

        "message":
            diagnosis_result.get(
                "message",
                "No diagnostic message available."
            ),

        "dependent_symptoms":
            diagnosis_result.get(
                "dependent_symptoms",
                []
            ),

        "resolution": None,

        "resolved_at": None
    }

    incidents = load_incidents()

    incidents.insert(
        0,
        incident
    )

    save_incidents(
        incidents
    )

    print(
        f"[INCIDENT CREATED] "
        f"{incident['id']} "
        f"({incident_service})"
    )

    return incident


# =========================================================
# Duplicate Protection
# =========================================================

def has_open_incident(
    root_cause,
    service
):
    """
    Prevent duplicate active incidents for the
    same service and root cause.
    """

    incidents = load_incidents()

    active_statuses = {
        "OPEN",
        "ESCALATED",
        "FAILED"
    }

    for incident in incidents:

        if (
            incident.get("service")
            == service

            and incident.get(
                "root_cause"
            )
            == root_cause

            and incident.get(
                "status"
            )
            in active_statuses
        ):

            return True

    return False


# =========================================================
# Incident Update After Remediation
# =========================================================

def update_incident_after_remediation(
    incident,
    remediation_result
):
    """
    Update incident state after remediation
    or escalation decision.
    """

    incidents = load_incidents()

    for item in incidents:

        if item.get("id") != incident.get(
            "id"
        ):
            continue

        if remediation_result.get(
            "success"
        ):

            item["status"] = (
                "RESOLVED"
            )

            item["resolution"] = (
                remediation_result.get(
                    "message",
                    "Remediation completed successfully."
                )
            )

            item["resolved_at"] = (
                get_timestamp()
            )

            print(
                f"[RESOLVED] "
                f"{item['resolution']}"
            )

        else:

            action = (
                remediation_result.get(
                    "action",
                    "ESCALATE"
                )
            )

            if action == "ESCALATE":

                item["status"] = (
                    "ESCALATED"
                )

                print(
                    f"[ESCALATED] "
                    f"{remediation_result.get('message')}"
                )

            else:

                item["status"] = (
                    "FAILED"
                )

                print(
                    f"[REMEDIATION FAILED] "
                    f"{remediation_result.get('message')}"
                )

            item["resolution"] = (
                remediation_result.get(
                    "message",
                    "Incident requires investigation."
                )
            )

        break

    save_incidents(
        incidents
    )


# =========================================================
# Incident Recovery
# =========================================================

def resolve_recovered_incidents(
    active_incident_keys
):
    """
    Resolve active incidents whose exact
    service/root-cause condition is no longer
    present in the latest health results.

    Each incident is evaluated independently.
    """

    incidents = load_incidents()

    updated = False

    active_statuses = {
        "OPEN",
        "ESCALATED",
        "FAILED"
    }

    for incident in incidents:

        if (
            incident.get("status")
            not in active_statuses
        ):
            continue

        incident_key = (
            incident.get("service"),
            incident.get("root_cause")
        )

        if (
            incident_key
            not in active_incident_keys
        ):

            incident["status"] = (
                "RESOLVED"
            )

            incident["resolution"] = (
                "The previously detected condition "
                "is no longer present in the latest "
                "infrastructure health checks."
            )

            incident["resolved_at"] = (
                get_timestamp()
            )

            print(
                f"[RECOVERED] "
                f"{incident.get('id')} - "
                f"{incident.get('root_cause')}"
            )

            updated = True

    if updated:

        save_incidents(
            incidents
        )


# =========================================================
# Diagnosis Display
# =========================================================

def print_single_diagnosis(
    diagnosis_result
):
    """
    Display one diagnosis result clearly.
    """

    print(
        f"[ROOT CAUSE] "
        f"{diagnosis_result.get('root_cause')}"
    )

    print(
        f"[SEVERITY] "
        f"{diagnosis_result.get('severity')}"
    )

    print(
        f"[CONFIDENCE] "
        f"{diagnosis_result.get('confidence')}"
    )

    print(
        f"[RECOMMENDED ACTION] "
        f"{diagnosis_result.get('recommended_action')}"
    )

    dependent_symptoms = (
        diagnosis_result.get(
            "dependent_symptoms",
            []
        )
    )

    if dependent_symptoms:

        print(
            "[DEPENDENT SYMPTOMS]"
        )

        for symptom in dependent_symptoms:

            print(
                f"    - {symptom}"
            )


# =========================================================
# Diagnosis Processing
# =========================================================

def process_diagnosis(
    diagnosis_result
):
    """
    Process one diagnosis independently.

    Handles:
    - duplicate protection
    - incident creation
    - safe remediation
    - escalation notification
    """

    root_cause = (
        diagnosis_result.get(
            "root_cause"
        )
    )

    if (
        not root_cause
        or root_cause == "NONE"
    ):
        return

    service = get_incident_service(
        diagnosis_result
    )

    print()
    print(
        "------------------------------------------"
    )

    print(
        f"[DIAGNOSIS] Processing "
        f"{root_cause}"
    )

    print_single_diagnosis(
        diagnosis_result
    )

    if has_open_incident(
        root_cause,
        service
    ):

        print(
            "[INFO] Matching active incident "
            "already exists."
        )

        return

    incident = create_incident(
        diagnosis_result,
        service=service
    )

    remediation_result = (
        execute_remediation(
            diagnosis_result
        )
    )

    update_incident_after_remediation(
        incident,
        remediation_result
    )

    if (
        remediation_result.get(
            "action"
        )
        == "ESCALATE"
    ):

        print(
            "[ALERT] Sending incident "
            "escalation notification..."
        )

        alert_result = (
            send_escalation_alert(
                incident,
                diagnosis_result
            )
        )

        if alert_result.get(
            "success"
        ):

            print(
                "[ALERT SENT] "
                f"{alert_result.get('message')}"
            )

        else:

            print(
                "[ALERT FAILED] "
                f"{alert_result.get('message')}"
            )


# =========================================================
# Build Active Diagnosis List
# =========================================================

def build_active_diagnoses(
    diagnosis_result
):
    """
    Convert Diagnosis Engine v2 output into
    one list of currently active diagnoses.
    """

    active_diagnoses = []

    primary_diagnosis = (
        diagnosis_result.get(
            "primary",
            {}
        )
    )

    if (
        primary_diagnosis.get(
            "root_cause"
        )
        not in [
            None,
            "NONE"
        ]
    ):

        active_diagnoses.append(
            primary_diagnosis
        )

    resource_alerts = (
        diagnosis_result.get(
            "alerts",
            []
        )
    )

    if isinstance(
        resource_alerts,
        list
    ):

        active_diagnoses.extend(
            resource_alerts
        )

    return active_diagnoses


# =========================================================
# Monitoring Loop
# =========================================================

def monitor():
    """
    Main InfraRescue continuous monitoring loop.

    Flow:

    Health Checks
        ↓
    Live Health Snapshot
        ↓
    Diagnosis Engine
        ↓
    Incident Correlation
        ↓
    Safe Remediation / Escalation
        ↓
    Recovery Detection
        ↓
    Dashboard
    """

    print(
        "=========================================="
    )

    print(
        "       InfraRescue Monitoring Agent"
    )

    print(
        "=========================================="
    )

    print(
        f"Monitoring: "
        f"{CONTAINER_NAME}"
    )

    print(
        f"Check interval: "
        f"{CHECK_INTERVAL} seconds"
    )

    print(
        "Press CTRL + C to stop monitoring"
    )

    print(
        "=========================================="
    )

    while True:

        try:

            print()

            print(
                f"[{get_timestamp()}] "
                f"Checking infrastructure..."
            )

            # -------------------------------------------------
            # Health checks
            # -------------------------------------------------

            (
                results,
                failures
            ) = get_failed_checks()

            # -------------------------------------------------
            # Save live health state for dashboard
            # -------------------------------------------------

            save_health_snapshot(
                results
            )

            # -------------------------------------------------
            # Display current failures
            # -------------------------------------------------

            if not failures:

                print(
                    "[HEALTHY] "
                    "No critical infrastructure "
                    "conditions detected"
                )

            else:

                print(
                    f"[FAILURE] "
                    f"{len(failures)} critical "
                    f"check(s) detected"
                )

                for failure in failures:

                    print(
                        f"    "
                        f"[{failure.get('status', 'unknown').upper()}] "
                        f"{failure.get('component', 'unknown')}: "
                        f"{failure.get('message', '')}"
                    )

            # -------------------------------------------------
            # Diagnosis Engine v2
            # -------------------------------------------------

            print(
                "[DIAGNOSIS] "
                "Analyzing infrastructure state..."
            )

            diagnosis_result = (
                diagnose(
                    results
                )
            )

            active_diagnoses = (
                build_active_diagnoses(
                    diagnosis_result
                )
            )

            # -------------------------------------------------
            # Build currently active incident keys
            # -------------------------------------------------

            active_incident_keys = {
                (
                    get_incident_service(
                        diagnosis_item
                    ),
                    diagnosis_item.get(
                        "root_cause"
                    )
                )
                for diagnosis_item
                in active_diagnoses
            }

            # -------------------------------------------------
            # Process current diagnoses
            # -------------------------------------------------

            if active_diagnoses:

                for diagnosis_item in (
                    active_diagnoses
                ):

                    process_diagnosis(
                        diagnosis_item
                    )

            else:

                print(
                    "[DIAGNOSIS] "
                    "No active incident condition detected"
                )

            # -------------------------------------------------
            # Recovery detection
            # -------------------------------------------------

            resolve_recovered_incidents(
                active_incident_keys
            )

            # -------------------------------------------------
            # Wait until next cycle
            # -------------------------------------------------

            time.sleep(
                CHECK_INTERVAL
            )

        except KeyboardInterrupt:

            print()

            print(
                "Monitoring stopped by user."
            )

            break

        except Exception as error:

            print(
                f"[AGENT ERROR] "
                f"{error}"
            )

            time.sleep(
                CHECK_INTERVAL
            )


# =========================================================
# Entry Point
# =========================================================

if __name__ == "__main__":
    monitor()