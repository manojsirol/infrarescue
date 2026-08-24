async function loadDashboard() {

    try {

        const statusResponse = await fetch("/api/status");
        const status = await statusResponse.json();

        document.getElementById("servicesChecked").textContent =
            status.services_checked;

        document.getElementById("runningServices").textContent =
            status.running_services;

        document.getElementById("activeIncidents").textContent =
            status.incidents;

        document.getElementById("systemHealth").textContent =
            status.health;


        const systemStatus = document.getElementById("systemStatus");

        systemStatus.textContent = status.system_status;


        if (status.incidents > 0) {

            systemStatus.classList.remove("healthy");
            systemStatus.classList.add("critical");

        } else {

            systemStatus.classList.remove("critical");
            systemStatus.classList.add("healthy");

        }


        const incidentResponse = await fetch("/api/incidents");

        const incidents = await incidentResponse.json();

        updateIncidents(incidents);

        updateApplicationStatus(incidents);

    }

    catch (error) {

        console.error("Dashboard update failed:", error);

    }

}


function updateApplicationStatus(incidents) {

    const applicationMessage =
        document.getElementById("applicationMessage");

    const applicationBadge =
        document.getElementById("applicationBadge");

    const applicationDot =
        document.getElementById("applicationDot");


    const unresolvedIncident = incidents.find(
        incident => incident.status !== "Resolved"
    );


    if (unresolvedIncident) {

        applicationMessage.textContent =
            unresolvedIncident.service + " is not running";

        applicationBadge.textContent =
            "INCIDENT";

        applicationBadge.className =
            "badge failed-badge";

        applicationDot.className =
            "status-dot failed-dot";

    }

    else {

        applicationMessage.textContent =
            "infrarescue-app is running";

        applicationBadge.textContent =
            "RUNNING";

        applicationBadge.className =
            "badge success-badge";

        applicationDot.className =
            "status-dot healthy-dot";

    }

}


function updateIncidents(incidents) {

    const incidentList =
        document.getElementById("incidentList");


    if (incidents.length === 0) {

        incidentList.innerHTML = `

            <div class="empty-state">
                No incidents detected.
                Infrastructure is operating normally.
            </div>

        `;

        return;

    }


    incidentList.innerHTML = "";


    incidents.forEach(incident => {

        const incidentCard =
            document.createElement("div");

        incidentCard.className =
            "incident-card";


        incidentCard.innerHTML = `

            <h3>${incident.id}</h3>

            <p>
                <strong>Service:</strong>
                ${incident.service}
            </p>

            <p>
                <strong>Detected:</strong>
                ${incident.detected_at}
            </p>

            <p>
                <strong>Problem:</strong>
                ${incident.problem}
            </p>

            <p>
                <strong>Classification:</strong>
                ${incident.classification}
            </p>

            <p>
                <strong>Action:</strong>
                ${incident.action}
            </p>

            <p>
                <strong>Status:</strong>
                ${incident.status}
            </p>

        `;


        incidentList.appendChild(
            incidentCard
        );

    });

}


loadDashboard();

setInterval(
    loadDashboard,
    5000
);