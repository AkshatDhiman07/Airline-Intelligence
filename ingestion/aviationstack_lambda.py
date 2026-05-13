"""
Travel Intelligence — Aviationstack Live Flight Ingestion
Fetches live flight data and lands raw JSON in S3 with date-partitioned keys.
"""
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import boto3
from datetime import datetime, timezone

# Initialize clients outside handler for connection reuse across warm invocations
s3 = boto3.client('s3')
secrets = boto3.client('secretsmanager')

# Read configuration from environment variables
RAW_BUCKET = os.environ['RAW_BUCKET']
SECRET_NAME = os.environ['SECRET_NAME']
API_LIMIT = int(os.environ.get('API_LIMIT', '100'))


def get_api_key():
    """Fetch the Aviationstack API key from Secrets Manager."""
    response = secrets.get_secret_value(SecretId=SECRET_NAME)
    secret_dict = json.loads(response['SecretString'])
    return secret_dict['AVIATIONSTACK_KEY']


def fetch_flights(api_key):
    """Call Aviationstack API and return parsed flight data."""
    params = urllib.parse.urlencode({
        'access_key': api_key,
        'limit': API_LIMIT
    })
    # NOTE: Aviationstack free tier requires HTTP, not HTTPS
    url = f"http://api.aviationstack.com/v1/flights?{params}"
    
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'travel-intel-lambda/1.0'}
    )
    
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode('utf-8')
        return json.loads(body)


def lambda_handler(event, context):
    """Main entry point. Fetch flights, save to S3, return summary."""
    print(f"Starting ingestion at {datetime.now(timezone.utc).isoformat()}")
    
    # Step 1: Get API key
    try:
        api_key = get_api_key()
    except Exception as e:
        print(f"❌ Failed to retrieve API key: {e}")
        raise
    
    # Step 2: Call Aviationstack
    try:
        data = fetch_flights(api_key)
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP error from Aviationstack: {e.code} {e.reason}")
        raise
    except Exception as e:
        print(f"❌ Failed to fetch flights: {e}")
        raise
    
    # Step 3: Validate response
    if 'error' in data:
        error_info = data['error']
        print(f"❌ API returned error: {error_info}")
        raise Exception(f"Aviationstack error: {error_info}")
    
    flights = data.get('data', [])
    pagination = data.get('pagination', {})
    record_count = len(flights)
    
    print(f"✅ Fetched {record_count} flights (total available: {pagination.get('total', 'unknown')})")
    
    # Step 4: Build a Hive-style partitioned S3 key
    now = datetime.now(timezone.utc)
    timestamp = now.strftime('%Y%m%dT%H%M%SZ')
    s3_key = (
        f"aviationstack/"
        f"year={now.year}/"
        f"month={now.month:02d}/"
        f"day={now.day:02d}/"
        f"hour={now.hour:02d}/"
        f"flights_{timestamp}.json"
    )
    
    # Step 5: Save to S3
    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=s3_key,
        Body=json.dumps(data, indent=2),
        ContentType='application/json',
        Metadata={
            'record_count': str(record_count),
            'ingestion_time': now.isoformat(),
            'source': 'aviationstack'
        }
    )
    
    s3_uri = f's3://{RAW_BUCKET}/{s3_key}'
    print(f"✅ Saved to {s3_uri}")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'records_ingested': record_count,
            's3_location': s3_uri,
            'timestamp': now.isoformat()
        })
    }
