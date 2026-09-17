async function loadDashboard() {

    try {

        const [
            statusResponse,
            healthResponse,
            incidentResponse
        ] = await Promise.all([
            fetch("/api/status"),
            fetch("/api/health"),
            fetch("/api/incidents")
        ]);


        if (
            !statusResponse.ok ||
            !healthResponse.ok ||
            !incidentResponse.ok
        ) {

            throw new Error(
                "Dashboard API request failed"
            );
        }


        const status =
            await statusResponse.json();

        const health =
            await healthResponse.json();

        const incidents =
            await incidentResponse.json();


        updateSummary(status);

        updateInfrastructure(
            health.components || []
        );

        updateIncidents(
            incidents
        );

    }

    catch (error) {

        console.error(
            "Dashboard update failed:",
            error
        );

        document.getElementById(
            "systemStatus"
        ).textContent =
            "DASHBOARD DATA UNAVAILABLE";
    }
}



function updateSummary(status) {

    document.getElementById(
        "servicesChecked"
    ).textContent =
        status.total_components;


    document.getElementById(
        "runningServices"
    ).textContent =
        status.healthy_components;


    document.getElementById(
        "activeIncidents"
    ).textContent =
        status.active_incidents;


    document.getElementById(
        "systemHealth"
    ).textContent =
        status.health;


    const systemStatus =
        document.getElementById(
            "systemStatus"
        );


    systemStatus.textContent =
        status.system_status;


    systemStatus.className =
        "system-status";


    const normalizedHealth =
        status.health.toLowerCase();


    if (
        normalizedHealth === "healthy"
    ) {

        systemStatus.classList.add(
            "healthy"
        );

    }

    else if (
        normalizedHealth === "warning"
    ) {

        systemStatus.classList.add(
            "warning"
        );

    }

    else {

        systemStatus.classList.add(
            "critical"
        );
    }


    const lastUpdated =
        document.getElementById(
            "lastUpdated"
        );


    if (status.last_updated) {

        lastUpdated.textContent =
            `Last agent check: ${status.last_updated} | Dashboard refresh: every 5 seconds`;

    }

    else {

        lastUpdated.textContent =
            "Waiting for InfraRescue agent health data...";
    }
}



function getStatusStyle(status) {

    switch (status) {

        case "healthy":

            return {
                dot: "healthy-dot",
                badge: "success-badge"
            };


        case "warning":

            return {
                dot: "warning-dot",
                badge: "warning-badge"
            };


        case "not_applicable":

            return {
                dot: "neutral-dot",
                badge: "neutral-badge"
            };


        case "unknown":

            return {
                dot: "neutral-dot",
                badge: "neutral-badge"
            };


        default:

            return {
                dot: "failed-dot",
                badge: "failed-badge"
            };
    }
}



function getComponentTitle(component) {

    const names = {

        ec2:
            "AWS EC2 Environment",

        host:
            "Host System",

        network:
            "Network Connectivity",

        cpu:
            "CPU Utilization",

        memory:
            "Memory Utilization",

        disk:
            "Disk Utilization",

        docker:
            "Docker Engine",

        container:
            "Application Container",

        port:
            "Application Port",

        application:
            "Application Health"
    };


    return (
        names[component] ||
        component
    );
}



function updateInfrastructure(
    components
) {

    const serviceList =
        document.getElementById(
            "serviceList"
        );


    if (
        !Array.isArray(components) ||
        components.length === 0
    ) {

        serviceList.innerHTML = `

            <div class="empty-state">

                No live infrastructure data available.

            </div>
        `;

        return;
    }


    serviceList.innerHTML = "";


    components.forEach(
        (component, index) => {

            const style =
                getStatusStyle(
                    component.status
                );


            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "service-item";


            let metric = "";


            if (
                component.usage_percent
                !== undefined
            ) {

                metric = `

                    <span class="metric">

                        ${component.usage_percent}%

                    </span>
                `;
            }


            item.innerHTML = `

                <div class="service-left">

                    <span
                        class="status-dot ${style.dot}"
                    ></span>

                    <div>

                        <h3>

                            ${index + 1}.
                            ${getComponentTitle(
                                component.component
                            )}

                        </h3>

                        <p>

                            ${component.message || "No information"}

                        </p>

                    </div>

                </div>


                <div class="service-right">

                    ${metric}

                    <span
                        class="badge ${style.badge}"
                    >

                        ${component.status
                            .replace("_", " ")
                            .toUpperCase()}

                    </span>

                </div>
            `;


            serviceList.appendChild(
                item
            );
        }
    );
}



function updateIncidents(
    incidents
) {

    const incidentList =
        document.getElementById(
            "incidentList"
        );


    if (
        !Array.isArray(incidents) ||
        incidents.length === 0
    ) {

        incidentList.innerHTML = `

            <div class="empty-state">

                No incidents detected.
                Infrastructure incident history is empty.

            </div>
        `;

        return;
    }


    incidentList.innerHTML = "";


    incidents.forEach(
        incident => {

            const incidentCard =
                document.createElement(
                    "div"
                );


            incidentCard.className =
                "incident-card";


            const symptoms =
                Array.isArray(
                    incident.dependent_symptoms
                )
                    ? incident
                        .dependent_symptoms
                        .join(", ")
                    : "None";


            incidentCard.innerHTML = `

                <div class="incident-header">

                    <h3>
                        ${incident.id}
                    </h3>

                    <span class="incident-status">

                        ${incident.status || "UNKNOWN"}

                    </span>

                </div>


                <p>

                    <strong>
                        Service:
                    </strong>

                    ${incident.service || "Unknown"}

                </p>


                <p>

                    <strong>
                        Detected:
                    </strong>

                    ${incident.timestamp || "Unknown"}

                </p>


                <p>

                    <strong>
                        Root Cause:
                    </strong>

                    ${incident.root_cause || "Unknown"}

                </p>


                <p>

                    <strong>
                        Severity:
                    </strong>

                    ${incident.severity || "Unknown"}

                </p>


                <p>

                    <strong>
                        Confidence:
                    </strong>

                    ${incident.confidence || "Unknown"}

                </p>


                <p>

                    <strong>
                        Recommended Action:
                    </strong>

                    ${incident.recommended_action || "None"}

                </p>


                <p>

                    <strong>
                        Message:
                    </strong>

                    ${incident.message || "No message"}

                </p>


                <p>

                    <strong>
                        Dependent Symptoms:
                    </strong>

                    ${symptoms || "None"}

                </p>


                <p>

                    <strong>
                        Resolution:
                    </strong>

                    ${incident.resolution || "Pending"}

                </p>


                <p>

                    <strong>
                        Resolved At:
                    </strong>

                    ${incident.resolved_at || "Pending"}

                </p>
            `;


            incidentList.appendChild(
                incidentCard
            );
        }
    );
}



loadDashboard();


setInterval(
    loadDashboard,
    5000
);