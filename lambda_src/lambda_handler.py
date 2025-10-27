import json
from scanner import get_idle_instances, auto_remediate, get_cost_summary
import os

def main(event, context):  # <- This MUST be at column 1 (no spaces before 'def')
    dry_run = os.environ.get('DRY_RUN', 'true').lower() == 'true'
    cost = get_cost_summary()
    idle = get_idle_instances()
    stopped = auto_remediate(dry_run=dry_run)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Scan complete. Cost: {cost}. Idle: {len(idle)}. Stopped: {stopped}. Dry run: {dry_run}'
        })
    }

if __name__ == '__main__':  # For local test
    print(main({}, None)['body'])