import json
import os
from datetime import datetime, timezone  # <- needed for UTC stamp
import boto3

from scanner import get_idle_instances, auto_remediate, get_cost_summary

# Exact topic ARN you provided
SNS_TOPIC_ARN = "arn:aws:sns:us-east-2:160564475450:cost-alerts"
sns = boto3.client("sns")

def main(event, context):  # <- This MUST be at column 1 (no spaces before 'def')
    dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'
    cost = get_cost_summary()
    idle = get_idle_instances()
    stopped = auto_remediate(dry_run=dry_run)

    # --- SNS alert (non-destructive) ---
    subject = f'AWS Cost Scan Report - {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}'
    message = (
        f'Scan complete:\n'
        f'- Last 30d cost: {cost}\n'
        f'- Idle instances: {len(idle)}\n'
        f'- Stopped: {stopped}\n'
        f'- Dry run: {dry_run}\n\n'
        f'Check Lambda logs for details.'
    )
    try:
        resp = sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
        print(f"[INFO] SNS published. MessageId={resp.get('MessageId')}")
    except Exception as e:
        # Do not fail the Lambda just because notification failed
        print(f"[ERROR] SNS publish failed: {e}")

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Scan complete. Cost: {cost}. Idle: {len(idle)}. Stopped: {stopped}. Dry run: {dry_run}'
        })
    }

if __name__ == '__main__':  # For local test
    print(main({}, None)['body'])
