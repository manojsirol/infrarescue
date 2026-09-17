from flask import Flask, render_template, jsonify
import json
import os


app = Flask(__name__)


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


ACTIVE_INCIDENT_STATUSES = {
    "OPEN",
    "ESCALATED",
    "FAILED"
}


def load_json_file(file_path, default):
    """
    Safely load a JSON file.
    """

    if not os.path.exists(file_path):
        return default

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except (
        json.JSONDecodeError,
        FileNotFoundError,
        OSError
    ):
        return default


def load_incidents():
    """
    Load InfraRescue incident history.
    """

    data = load_json_file(
        INCIDENT_FILE,
        []
    )

    if isinstance(data, list):
        return data

    return []


def load_health():
    """
    Load the latest live infrastructure health snapshot.
    """

    data = load_json_file(
        HEALTH_FILE,
        {}
    )

    if isinstance(data, dict):
        return data

    return {}


@app.route("/")
def index():
    return render_template(
        "index.html"
    )


@app.route("/api/incidents")
def incidents():
    return jsonify(
        load_incidents()
    )


@app.route("/api/health")
def health():
    return jsonify(
        load_health()
    )


@app.route("/api/status")
def status():

    incidents = load_incidents()
    health_data = load_health()

    active_incidents = [
        incident
        for incident in incidents
        if incident.get("status")
        in ACTIVE_INCIDENT_STATUSES
    ]

    components = health_data.get(
        "components",
        []
    )

    healthy_count = sum(
        1
        for component in components
        if component.get("status") == "healthy"
    )

    warning_count = sum(
        1
        for component in components
        if component.get("status") == "warning"
    )

    critical_count = sum(
        1
        for component in components
        if component.get("status") in {
            "critical",
            "down",
            "unhealthy"
        }
    )

    not_applicable_count = sum(
        1
        for component in components
        if component.get("status")
        == "not_applicable"
    )

    overall_status = health_data.get(
        "overall_status",
        "unknown"
    )

    if overall_status == "critical":
        system_status = (
            "CRITICAL INFRASTRUCTURE CONDITION"
        )
        health = "Critical"

    elif overall_status == "warning":
        system_status = (
            "INFRASTRUCTURE DEGRADED"
        )
        health = "Warning"

    elif overall_status == "healthy":
        system_status = (
            "ALL SYSTEMS OPERATIONAL"
        )
        health = "Healthy"

    else:
        system_status = (
            "INFRASTRUCTURE STATUS UNKNOWN"
        )
        health = "Unknown"

    return jsonify({
        "system_status": system_status,
        "health": health,
        "total_components": len(
            components
        ),
        "healthy_components": healthy_count,
        "warning_components": warning_count,
        "critical_components": critical_count,
        "not_applicable_components":
            not_applicable_count,
        "active_incidents": len(
            active_incidents
        ),
        "last_updated": health_data.get(
            "timestamp"
        )
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )