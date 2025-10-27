import boto3
from datetime import datetime, timedelta
import json
import argparse

# AWS clients
ec2 = boto3.client('ec2')
cloudwatch = boto3.client('cloudwatch')
ce = boto3.client('ce')  # Cost Explorer

def get_idle_instances(days_idle=3):
    """Find EC2 instances idle for X days (low CPU)."""
    idle_threshold = days_idle * 24 * 60 * 60  # Seconds
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(seconds=idle_threshold)
    
    # Get all running instances
    response = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    idle_instances = []
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            # Check average CPU over period
            metric = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # Hourly
                Statistics=['Average']
            )
            avg_cpu = sum(d['Average'] for d in metric['Datapoints']) / max(len(metric['Datapoints']), 1)
            
            if avg_cpu < 5:  # Idle if <5%
                idle_instances.append({
                    'id': instance_id,
                    'type': instance['InstanceType'],
                    'launch_time': instance['LaunchTime'].isoformat(),
                    'estimated_monthly_cost': f"${0.01 * 30:.2f}"  # Rough t3.micro estimate; customize later
                })
    
    return idle_instances

def get_cost_summary():
    """Quick cost peek for last month."""
    response = ce.get_cost_and_usage(
        TimePeriod={'Start': (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'), 'End': datetime.utcnow().strftime('%Y-%m-%d')},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )
    total_cost = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
    return f"${float(total_cost):.2f}"

def auto_remediate(dry_run=True):
    """Stop idle instances. dry_run=True just simulates."""
    idle = get_idle_instances()  # Reuse our scan
    stopped = 0
    for inst in idle:
        if dry_run:
            print(f"DRY RUN: Would stop {inst['id']} ({inst['type']}) to save {inst['estimated_monthly_cost']}/mo")
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
    parser.add_argument('--remediate', action='store_true', help="Stop idle instances instead of dry run")
    args = parser.parse_args()

    print("=== AWS Cost Optimization Report ===")
    print(f"Total spend last 30 days: {get_cost_summary()}")

    idle = get_idle_instances()
    if idle:
        print("\nIdle EC2 Instances (potential to stop/resize):")
        for inst in idle:
            print(f"- {inst['id']} ({inst['type']}): Idle since {inst['launch_time'][:10]}, save {inst['estimated_monthly_cost']}/month")
        
        print("\nRemediation preview:")
        auto_remediate(dry_run=True)  # Simulates—change to False to actually stop
    else:
        print("\nNo idle instances found—nice!")

if __name__ == '__main__':
    main()

