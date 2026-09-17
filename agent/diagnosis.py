"""
InfraRescue Diagnosis Engine v2

The health-check layer reports infrastructure symptoms.

This module correlates those symptoms and determines:
1. The primary application/infrastructure root cause.
2. Independent resource and connectivity alerts.

Diagnosis never performs remediation directly.
"""


def build_status_map(results):
    """
    Convert health-check results into a
    component -> result mapping.
    """

    return {
        result["component"]: result
        for result in results
    }


def create_diagnosis(
    root_cause,
    known_issue,
    severity,
    confidence,
    recommended_action,
    message,
    dependent_symptoms=None
):
    """
    Return a diagnosis in a consistent format.
    """

    return {
        "root_cause": root_cause,
        "known_issue": known_issue,
        "severity": severity,
        "confidence": confidence,
        "recommended_action": recommended_action,
        "message": message,
        "dependent_symptoms": dependent_symptoms or []
    }


def diagnose_primary_failure(status_map):
    """
    Diagnose the main application infrastructure path.

    Priority:

    Docker
        ↓
    Container
        ↓
    Port
        ↓
    Application
    """

    docker = status_map.get(
        "docker",
        {}
    )

    container = status_map.get(
        "container",
        {}
    )

    port = status_map.get(
        "port",
        {}
    )

    application = status_map.get(
        "application",
        {}
    )


    docker_status = docker.get(
        "status",
        "unknown"
    )

    container_status = container.get(
        "status",
        "unknown"
    )

    port_status = port.get(
        "status",
        "unknown"
    )

    application_status = application.get(
        "status",
        "unknown"
    )


    # -----------------------------------------------------
    # Docker unavailable
    # -----------------------------------------------------

    if docker_status == "down":

        return create_diagnosis(
            root_cause="DOCKER_UNAVAILABLE",
            known_issue=True,
            severity="HIGH",
            confidence="HIGH",
            recommended_action="START_DOCKER",
            message=(
                "Docker is unavailable or not responding."
            ),
            dependent_symptoms=[
                "Container state may be unavailable",
                "Application may be unavailable"
            ]
        )


    # -----------------------------------------------------
    # Container stopped
    # -----------------------------------------------------

    if (
        docker_status == "healthy"
        and container_status == "down"
    ):

        symptoms = []

        if port_status == "down":
            symptoms.append(
                "Application port is unavailable"
            )

        if application_status in [
            "down",
            "unhealthy"
        ]:
            symptoms.append(
                "Application health endpoint is unavailable"
            )

        return create_diagnosis(
            root_cause="CONTAINER_STOPPED",
            known_issue=True,
            severity="HIGH",
            confidence="HIGH",
            recommended_action="RESTART_CONTAINER",
            message=(
                "Docker is healthy but the application "
                "container is not running."
            ),
            dependent_symptoms=symptoms
        )


    # -----------------------------------------------------
    # Container running but port unavailable
    # -----------------------------------------------------

    if (
        container_status == "healthy"
        and port_status == "down"
    ):

        return create_diagnosis(
            root_cause="APPLICATION_PORT_UNAVAILABLE",
            known_issue=False,
            severity="HIGH",
            confidence="MEDIUM",
            recommended_action="ESCALATE",
            message=(
                "The container is running but the expected "
                "application port is not accepting connections."
            ),
            dependent_symptoms=[
                "Application may not have started correctly"
            ]
        )


    # -----------------------------------------------------
    # Application health failure
    # -----------------------------------------------------

    if (
        container_status == "healthy"
        and port_status == "healthy"
        and application_status in [
            "down",
            "unhealthy"
        ]
    ):

        return create_diagnosis(
            root_cause="APPLICATION_HEALTH_FAILURE",
            known_issue=False,
            severity="HIGH",
            confidence="HIGH",
            recommended_action="ESCALATE",
            message=(
                "Infrastructure is reachable but the "
                "application health endpoint is failing."
            ),
            dependent_symptoms=[]
        )


    # -----------------------------------------------------
    # Application path healthy
    # -----------------------------------------------------

    if (
        docker_status == "healthy"
        and container_status == "healthy"
        and port_status == "healthy"
        and application_status == "healthy"
    ):

        return create_diagnosis(
            root_cause="NONE",
            known_issue=False,
            severity="NONE",
            confidence="HIGH",
            recommended_action="NONE",
            message=(
                "Application infrastructure path is healthy."
            ),
            dependent_symptoms=[]
        )


    # -----------------------------------------------------
    # Unknown application condition
    # -----------------------------------------------------

    return create_diagnosis(
        root_cause="UNKNOWN_FAILURE",
        known_issue=False,
        severity="HIGH",
        confidence="LOW",
        recommended_action="ESCALATE",
        message=(
            "InfraRescue detected an unhealthy application "
            "state but no known diagnosis rule matched."
        ),
        dependent_symptoms=[]
    )


def diagnose_resource_alerts(status_map):
    """
    Detect independent host/resource conditions.

    These conditions are not automatically repaired.
    """

    alerts = []


    # -----------------------------------------------------
    # Network
    # -----------------------------------------------------

    network = status_map.get(
        "network",
        {}
    )

    if network.get("status") == "down":

        alerts.append(
            create_diagnosis(
                root_cause="NETWORK_CONNECTIVITY_FAILURE",
                known_issue=True,
                severity="HIGH",
                confidence="HIGH",
                recommended_action="ESCALATE",
                message=network.get(
                    "message",
                    "Network connectivity is unavailable."
                ),
                dependent_symptoms=[]
            )
        )


    # -----------------------------------------------------
    # CPU
    # -----------------------------------------------------

    cpu = status_map.get(
        "cpu",
        {}
    )

    if cpu.get("status") == "critical":

        alerts.append(
            create_diagnosis(
                root_cause="CPU_USAGE_CRITICAL",
                known_issue=True,
                severity="HIGH",
                confidence="HIGH",
                recommended_action="ESCALATE",
                message=cpu.get(
                    "message",
                    "CPU usage is critically high."
                ),
                dependent_symptoms=[]
            )
        )


    # -----------------------------------------------------
    # Memory
    # -----------------------------------------------------

    memory = status_map.get(
        "memory",
        {}
    )

    if memory.get("status") == "critical":

        alerts.append(
            create_diagnosis(
                root_cause="MEMORY_USAGE_CRITICAL",
                known_issue=True,
                severity="HIGH",
                confidence="HIGH",
                recommended_action="ESCALATE",
                message=memory.get(
                    "message",
                    "Memory usage is critically high."
                ),
                dependent_symptoms=[]
            )
        )


    # -----------------------------------------------------
    # Disk
    # -----------------------------------------------------

    disk = status_map.get(
        "disk",
        {}
    )

    if disk.get("status") == "critical":

        alerts.append(
            create_diagnosis(
                root_cause="DISK_USAGE_CRITICAL",
                known_issue=True,
                severity="HIGH",
                confidence="HIGH",
                recommended_action="ESCALATE",
                message=disk.get(
                    "message",
                    "Disk usage is critically high."
                ),
                dependent_symptoms=[]
            )
        )


    return alerts


def diagnose(results):
    """
    Perform complete InfraRescue diagnosis.

    Returns:

    {
        "primary": {...},
        "alerts": [...]
    }
    """

    status_map = build_status_map(
        results
    )

    primary = diagnose_primary_failure(
        status_map
    )

    alerts = diagnose_resource_alerts(
        status_map
    )

    return {
        "primary": primary,
        "alerts": alerts
    }


if __name__ == "__main__":

    from healthcheck import run_all_checks

    results = run_all_checks()

    diagnosis = diagnose(
        results
    )

    print()
    print(
        "=============================================="
    )
    print(
        "         INFRARESCUE DIAGNOSIS ENGINE"
    )
    print(
        "=============================================="
    )

    print()
    print("PRIMARY DIAGNOSIS")
    print(
        diagnosis["primary"]
    )

    print()
    print("RESOURCE ALERTS")

    if diagnosis["alerts"]:

        for alert in diagnosis["alerts"]:
            print(alert)

    else:
        print("None")

    print()
    print(
        "=============================================="
    )