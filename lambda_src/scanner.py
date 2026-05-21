import boto3
from datetime import datetime, timedelta, timezone
import argparse

ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')
ce = boto3.client('ce')

INSTANCE_HOURLY_PRICING = {
    't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464, 't2.large': 0.0928,
    't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832,
    't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
    't3a.micro': 0.0094, 't3a.small': 0.0188, 't3a.medium': 0.0376,
    'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384, 'm5.4xlarge': 0.768,
    'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
    'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504,
}


def _estimate_monthly_cost(instance_type: str) -> str:
    hourly = INSTANCE_HOURLY_PRICING.get(instance_type, 0.05)
    return f"${hourly * 24 * 30:.2f}"


def get_idle_instances(days_idle=3):
    """Find EC2 instances idle for X days (CPU < 5% average)."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_idle)
    idle_instances = []

    paginator = ec2.get_paginator('describe_instances')
    pages = paginator.paginate(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )

    for page in pages:
        for reservation in page['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                try:
                    metric = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average'],
                    )
                    datapoints = metric['Datapoints']
                    avg_cpu = (
                        sum(d['Average'] for d in datapoints) / len(datapoints)
                        if datapoints else 0.0
                    )
                    if avg_cpu < 5:
                        idle_instances.append({
                            'id': instance_id,
                            'type': instance_type,
                            'launch_time': instance['LaunchTime'].isoformat(),
                            'avg_cpu': round(avg_cpu, 2),
                            'estimated_monthly_cost': _estimate_monthly_cost(instance_type),
                        })
                except Exception as e:
                    print(f"Warning: could not get metrics for {instance_id}: {e}")

    return idle_instances


def get_cost_summary():
    """Return total AWS spend for the last 30 days."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    try:
        response = ce.get_cost_and_usage(
            TimePeriod={
                'Start': start.strftime('%Y-%m-%d'),
                'End': end.strftime('%Y-%m-%d'),
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
        )
        results = response.get('ResultsByTime', [])
        if not results:
            return '$0.00'
        total = sum(float(r['Total']['UnblendedCost']['Amount']) for r in results)
        return f'${total:.2f}'
    except Exception as e:
        print(f"Warning: could not retrieve cost data: {e}")
        return 'N/A'


def auto_remediate(dry_run=True):
    """Stop idle instances. dry_run=True simulates only."""
    idle = get_idle_instances()
    stopped = 0
    for inst in idle:
        if dry_run:
            print(
                f"DRY RUN: Would stop {inst['id']} ({inst['type']},"
                f" avg CPU {inst['avg_cpu']}%) — saves {inst['estimated_monthly_cost']}/mo"
            )
        else:
            try:
                ec2.stop_instances(InstanceIds=[inst['id']])
                print(f"STOPPED: {inst['id']} ({inst['type']})")
                stopped += 1
            except Exception as e:
                print(f"Error stopping {inst['id']}: {e}")
    if stopped > 0:
        print(f"\nRemediation complete: {stopped} instances stopped.")
    return stopped


def main():
    parser = argparse.ArgumentParser(description="AWS EC2 Cost Optimizer")
    parser.add_argument('--remediate', action='store_true', help="Stop idle instances (live mode)")
    args = parser.parse_args()

    print("=== AWS Cost Optimization Report ===")
    print(f"Total spend last 30 days: {get_cost_summary()}")

    idle = get_idle_instances()
    if idle:
        print("\nIdle EC2 Instances (potential to stop/resize):")
        for inst in idle:
            print(
                f"- {inst['id']} ({inst['type']}, avg CPU {inst['avg_cpu']}%):"
                f" idle since {inst['launch_time'][:10]}, save {inst['estimated_monthly_cost']}/month"
            )

        dry_run = not args.remediate
        print(f"\n{'Remediation preview (dry run):' if dry_run else 'Running live remediation:'}")
        auto_remediate(dry_run=dry_run)
    else:
        print("\nNo idle instances found—nice!")

if __name__ == '__main__':
    main()
