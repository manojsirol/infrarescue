import os
from datetime import datetime

import boto3
from botocore.exceptions import BotoCoreError, ClientError


AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")

SNS_TOPIC_ARN = os.getenv(
    "INFRARESCUE_SNS_TOPIC_ARN"
)


def build_alert_message(incident, diagnosis_result):
    """
    Build a readable SNS alert for an InfraRescue incident.
    """

    symptoms = diagnosis_result.get(
        "dependent_symptoms",
        []
    )

    if symptoms:
        symptom_text = "\n".join(
            f"- {symptom}"
            for symptom in symptoms
        )
    else:
        symptom_text = "None"

    return (
        "InfraRescue Incident Escalation\n"
        "================================\n\n"
        f"Incident ID: {incident.get('id')}\n"
        f"Service: {incident.get('service')}\n"
        f"Time: {incident.get('timestamp')}\n\n"
        f"Root Cause: {diagnosis_result.get('root_cause')}\n"
        f"Severity: {diagnosis_result.get('severity')}\n"
        f"Confidence: {diagnosis_result.get('confidence')}\n"
        f"Known Issue: {diagnosis_result.get('known_issue')}\n"
        f"Recommended Action: "
        f"{diagnosis_result.get('recommended_action')}\n\n"
        f"Message:\n"
        f"{diagnosis_result.get('message')}\n\n"
        f"Dependent Symptoms:\n"
        f"{symptom_text}\n\n"
        "Automatic remediation was not performed because "
        "the incident requires engineer investigation.\n"
    )


def send_escalation_alert(incident, diagnosis_result):
    """
    Publish an incident escalation alert to AWS SNS.

    AWS credentials are obtained automatically from the
    EC2 IAM role. No static access keys are required.
    """

    if not SNS_TOPIC_ARN:
        return {
            "success": False,
            "message": (
                "INFRARESCUE_SNS_TOPIC_ARN "
                "environment variable is not configured."
            )
        }

    subject = (
        f"InfraRescue {diagnosis_result.get('severity')} Alert - "
        f"{diagnosis_result.get('root_cause')}"
    )

    message = build_alert_message(
        incident,
        diagnosis_result
    )

    try:
        sns = boto3.client(
            "sns",
            region_name=AWS_REGION
        )

        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject[:100],
            Message=message
        )

        return {
            "success": True,
            "message": "SNS escalation alert published successfully.",
            "message_id": response.get("MessageId"),
            "sent_at": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        }

    except (BotoCoreError, ClientError) as error:
        return {
            "success": False,
            "message": (
                f"Failed to publish SNS escalation alert: "
                f"{error}"
            )
        }

    except Exception as error:
        return {
            "success": False,
            "message": (
                f"Unexpected escalation error: {error}"
            )
        }
