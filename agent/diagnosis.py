"""
InfraRescue Diagnosis Engine

The health-check layer reports symptoms.
This module correlates those symptoms and determines
the most probable root cause.

Phase 2 intentionally performs diagnosis only.
It does not execute remediation.
"""


def build_status_map(results):
    """
    Convert the list returned by healthcheck.py into
    an easier-to-use component -> result mapping.

    Example:

    [
        {"component": "docker", "status": "healthy"},
        {"component": "container", "status": "down"}
    ]

    becomes:

    {
        "docker": {...},
        "container": {...}
    }
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
    Return every diagnosis in the same structured format.
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


def diagnose(results):
    """
    Analyze infrastructure health-check results
    and determine the most probable root cause.
    """

    status_map = build_status_map(results)

    docker = status_map.get("docker", {})
    container = status_map.get("container", {})
    port = status_map.get("port", {})
    application = status_map.get("application", {})
    disk = status_map.get("disk", {})

    docker_status = docker.get("status", "unknown")
    container_status = container.get("status", "unknown")
    port_status = port.get("status", "unknown")
    application_status = application.get("status", "unknown")
    disk_status = disk.get("status", "unknown")

    # -----------------------------------------------------
    # Rule 1 — Docker unavailable
    # -----------------------------------------------------

    if docker_status == "down":

        return create_diagnosis(
            root_cause="DOCKER_UNAVAILABLE",
            known_issue=True,
            severity="HIGH",
            confidence="HIGH",
            recommended_action="START_DOCKER",
            message="Docker is unavailable or not responding.",
            dependent_symptoms=[
                "Container state may be unavailable",
                "Application may be unavailable"
            ]
        )

    # -----------------------------------------------------
    # Rule 2 — Container stopped
    # -----------------------------------------------------

    if (
        docker_status == "healthy"
        and container_status == "down"
    ):

        symptoms = []

        if port_status == "down":
            symptoms.append("Application port is unavailable")

        if application_status in ["down", "unhealthy"]:
            symptoms.append("Application health endpoint is unavailable")

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
    # Rule 3 — Container running but port unavailable
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
    # Rule 4 — Port available but application unhealthy
    # -----------------------------------------------------

    if (
        container_status == "healthy"
        and port_status == "healthy"
        and application_status in ["down", "unhealthy"]
    ):

        return create_diagnosis(
            root_cause="APPLICATION_HEALTH_FAILURE",
            known_issue=False,
            severity="HIGH",
            confidence="HIGH",
            recommended_action="ESCALATE",
            message=(
                "Infrastructure is reachable but the "
                "application health check is failing."
            ),
            dependent_symptoms=[]
        )

    # -----------------------------------------------------
    # Rule 5 — Critical disk usage
    # -----------------------------------------------------

    if disk_status == "critical":

        return create_diagnosis(
            root_cause="DISK_USAGE_CRITICAL",
            known_issue=True,
            severity="MEDIUM",
            confidence="HIGH",
            recommended_action="ESCALATE",
            message="Disk usage has reached the critical threshold.",
            dependent_symptoms=[]
        )

    # -----------------------------------------------------
    # No actual outage detected
    # -----------------------------------------------------

    infrastructure_failures = [
        docker_status,
        container_status,
        port_status,
        application_status
    ]

    if all(
        status == "healthy"
        for status in infrastructure_failures
    ):

        return create_diagnosis(
            root_cause="NONE",
            known_issue=False,
            severity="NONE",
            confidence="HIGH",
            recommended_action="NONE",
            message="No infrastructure failure detected.",
            dependent_symptoms=[]
        )

    # -----------------------------------------------------
    # Unknown condition
    # -----------------------------------------------------

    return create_diagnosis(
        root_cause="UNKNOWN_FAILURE",
        known_issue=False,
        severity="HIGH",
        confidence="LOW",
        recommended_action="ESCALATE",
        message=(
            "InfraRescue detected an unhealthy state but "
            "no known diagnosis rule matched."
        ),
        dependent_symptoms=[]
    )