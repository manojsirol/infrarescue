# InfraRescue

> **Automated Infrastructure Incident Detection, Diagnosis & Recovery Platform**

InfraRescue is a DevOps/AIOps project that monitors a Dockerized application, detects infrastructure failures, identifies the probable root cause, automatically remediates known issues, verifies recovery, and escalates unknown failures through AWS SNS.

The goal is to automate the **first level of incident response** and reduce manual troubleshooting and recovery time.

---

## Architecture

```text
                    AWS
                     |
              Terraform (IaC)
                     |
                     v
              EC2 + IAM Role
                     |
        +------------+-------------+
        |                          |
        v                          v
      Docker                InfraRescue Agent
        |                          |
        v                          v
   Flask Application        Health Monitoring
                                   |
                                   v
                            Failure Detection
                                   |
                                   v
                           Root-Cause Diagnosis
                                   |
                         +---------+---------+
                         |                   |
                    Known & Safe        Unknown/Unsafe
                         |                   |
                         v                   v
                  Auto Remediation       AWS SNS
                  Python + Ansible          |
                         |                   v
                         v              Email Alert
                    Verification
                         |
                         v
                      RESOLVED
```

---

## Key Features

- **Multi-layer health monitoring** — Docker, container, application port, HTTP health endpoint, and disk usage.
- **Root-cause diagnosis** — distinguishes the primary failure from dependent symptoms.
- **Safe auto-remediation** — automatically fixes only predefined and approved failures.
- **Ansible recovery runbooks** — restores infrastructure services such as Docker.
- **Recovery verification** — validates container, port, and application health after remediation.
- **AWS SNS escalation** — unknown or unsafe failures are escalated instead of blindly fixed.
- **Duplicate alert suppression** — prevents repeated alerts for the same active incident.
- **Incident lifecycle tracking** — incidents move through `OPEN`, `ESCALATED`, and `RESOLVED`.
- **Persistent monitoring** — the agent runs as a Linux `systemd` service.

---

## Tech Stack

| Area | Technology |
|---|---|
| Cloud | AWS EC2, VPC, IAM, SNS |
| Infrastructure as Code | Terraform |
| Configuration & Recovery | Ansible |
| Containers | Docker, Docker Compose |
| Monitoring & Automation | Python |
| Application | Flask |
| Service Management | systemd |
| Version Control | Git & GitHub |

---

## Tested Failure Scenarios

| Failure | Diagnosis | Action | Result |
|---|---|---|---|
| Application container stopped | `CONTAINER_STOPPED` | Automatic container restart | Recovered |
| Docker service stopped | `DOCKER_UNAVAILABLE` | Ansible Docker recovery | Recovered |
| Application `/health` returns HTTP 500 | `APPLICATION_HEALTH_FAILURE` | AWS SNS escalation | Engineer alerted |
| Same failure remains active | Existing incident detected | Duplicate alert suppressed | No alert flood |
| EC2 stop/start | Services restart | systemd + Docker recovery | Monitoring restored |

These scenarios were deliberately triggered to test InfraRescue's detection, diagnosis, remediation, escalation, and recovery workflow.

---

## Incident Response Flow

```text
PROBLEM
   ↓
DETECT
   ↓
DIAGNOSE
   ↓
SAFE TO AUTO-FIX?
   ↓             ↓
  YES            NO
   ↓             ↓
REMEDIATE     ESCALATE
   ↓             ↓
VERIFY        AWS SNS
   ↓             ↓
RESOLVED      ENGINEER
```

---

## Project Structure

```text
infrarescue/
├── agent/                    # Monitoring and recovery engine
│   ├── healthcheck.py
│   ├── diagnosis.py
│   ├── remediation.py
│   ├── escalation.py
│   └── monitor.py
│
├── app/                      # Dockerized Flask application
├── ansible/runbooks/         # Deployment and recovery automation
├── infrastructure/terraform/ # AWS Infrastructure as Code
├── dashboard/                # Incident dashboard
├── incidents/                # Runtime incident records
├── docker-compose.yml
└── README.md
```

---

## Security

InfraRescue follows several security practices:

- AWS authentication uses an **EC2 IAM role** instead of static access keys.
- SNS permissions are scoped to the required notification topic.
- Server-side runtime configuration uses restricted file permissions.
- Terraform state, local inventory, runtime incidents, environment files, and private keys are excluded from Git.
- The application monitoring port does not need to be publicly exposed for the monitoring agent.

Sensitive/local files such as these are intentionally ignored:

```text
.env
*.pem
*.key
.aws/
.venv/
ansible/inventory.ini
terraform.tfstate
terraform.tfvars
incidents/incidents.json
```

---

## Current Status

**Implemented**

`Monitoring` → `Diagnosis` → `Incident Detection` → `Auto Remediation` → `Ansible Recovery` → `Verification` → `SNS Escalation` → `Recovery Lifecycle`

**Next**

- Incident monitoring dashboard
- CI/CD pipeline
- Additional infrastructure checks
- Additional safe recovery runbooks
- Monitoring and recovery metrics

---

## Project Goal

InfraRescue demonstrates a practical DevOps incident-response workflow combining:

**AWS + Linux + Python + Docker + Terraform + Ansible + Monitoring + Automation**

Rather than automatically restarting everything, InfraRescue first diagnoses the problem and only performs automated remediation when the failure is known and considered safe.

---
