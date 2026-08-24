from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INCIDENT_FILE = os.path.join(BASE_DIR, "incidents", "incidents.json")


def load_incidents():
    if not os.path.exists(INCIDENT_FILE):
        return []

    try:
        with open(INCIDENT_FILE, "r") as file:
            data = json.load(file)
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/incidents")
def incidents():
    return jsonify(load_incidents())


@app.route("/api/status")
def status():
    incidents = load_incidents()

    total_incidents = len(incidents)

    unresolved_incidents = [
        incident for incident in incidents
        if incident.get("status") != "Resolved"
    ]

    if unresolved_incidents:
        system_status = "INCIDENT DETECTED"
        health = "Critical"
    else:
        system_status = "ALL SYSTEMS OPERATIONAL"
        health = "Healthy"

    return jsonify({
        "system_status": system_status,
        "health": health,
        "services_checked": 4,
        "running_services": 4 - len(unresolved_incidents),
        "incidents": len(unresolved_incidents),
        "total_incidents": total_incidents
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True
    )