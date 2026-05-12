"""
Travel Intelligence — REST API (STUB)

Status: Designed but not deployed (Step 8 of master plan).
Architecture is complete; deployment to API Gateway + Lambda is queued
for production hardening phase.

Intended endpoints:
  POST /predict-delay         → ML inference (delay probability)
  GET  /route-insights/{id}   → Route performance metrics from Athena
  GET  /booking-recommendation/{route_id} → Best hour to fly that route
  GET  /surge-alerts          → Current cancellation/delay surges
  GET  /health                → Health check

This file contains the handler stubs. Production deployment requires:
  1. Package this with awswrangler + sklearn into Lambda layer (~150MB)
  2. Provision API Gateway REST API
  3. Map endpoints to this Lambda
  4. Configure API key authentication + usage plans
  5. Deploy via SAM/Terraform

Estimated effort: 6-8 hours.
"""

import json
import os
import boto3
import joblib
import pandas as pd
from io import BytesIO

# ─────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────
S3_BUCKET = os.environ.get('S3_BUCKET', 'airline-processed-flight-data')
MODEL_KEY = os.environ.get('MODEL_KEY', 'ml-models/delay_predictor_v1.pkl')
COLUMNS_KEY = os.environ.get('COLUMNS_KEY', 'ml-models/feature_columns_v1.pkl')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'travel_intel')

# Globals — loaded once per Lambda container (warm start optimization)
_model = None
_columns = None


def load_model():
    """Lazy-load model artifacts from S3, cached across warm invocations."""
    global _model, _columns
    if _model is None:
        s3 = boto3.client('s3')
        model_bytes = s3.get_object(Bucket=S3_BUCKET, Key=MODEL_KEY)['Body'].read()
        cols_bytes = s3.get_object(Bucket=S3_BUCKET, Key=COLUMNS_KEY)['Body'].read()
        _model = joblib.load(BytesIO(model_bytes))
        _columns = joblib.load(BytesIO(cols_bytes))
    return _model, _columns


def predict_delay_handler(event, context):
    """
    POST /predict-delay
    
    Input (JSON body):
      {
        "airline_code": "WN",
        "origin": "LAX",
        "dest": "JFK",
        "dep_hour": 18,
        "day_of_week_num": 5,
        "month_num": 6,
        "is_weekend": false,
        "distance": 2475
      }
    
    Output:
      {
        "delay_probability": 0.34,
        "risk_level": "MEDIUM",
        "model_version": "v1",
        "model_auc": 0.67
      }
    """
    model, columns = load_model()
    body = json.loads(event.get('body', '{}'))
    
    # Build input DataFrame
    input_df = pd.DataFrame([body])
    X = pd.get_dummies(input_df, columns=['airline_code', 'origin', 'dest'])
    X = X.reindex(columns=columns, fill_value=0)
    
    # Predict
    prob = float(model.predict_proba(X)[0, 1])
    
    risk = 'HIGH' if prob > 0.4 else ('MEDIUM' if prob > 0.2 else 'LOW')
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'delay_probability': round(prob, 4),
            'risk_level': risk,
            'model_version': 'v1',
            'model_auc': 0.6673
        })
    }


def route_insights_handler(event, context):
    """
    GET /route-insights/{route_id}
    
    Returns aggregated performance for a specific route from Athena
    flights_clean view.
    
    Implementation pending API Gateway deployment.
    """
    return {
        'statusCode': 501,
        'body': json.dumps({
            'error': 'Not Implemented',
            'message': 'Endpoint designed but deployment pending. See README.md > Future Work.'
        })
    }


def booking_recommendation_handler(event, context):
    """
    GET /booking-recommendation/{route_id}
    
    Returns the best hour-of-day to fly for the requested route
    based on historical delay patterns.
    
    Implementation pending API Gateway deployment.
    """
    return {
        'statusCode': 501,
        'body': json.dumps({
            'error': 'Not Implemented',
            'message': 'Endpoint designed but deployment pending. See README.md > Future Work.'
        })
    }


def health_handler(event, context):
    """GET /health — Health check."""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'ok',
            'service': 'travel-intel-api',
            'version': '1.0.0-mvp'
        })
    }


# ─────────────────────────────────────────────────────────
# Router for single-Lambda deployment pattern
# ─────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Routes incoming API Gateway requests to the correct handler.
    
    Supports both REST API Gateway and HTTP API Gateway event formats.
    """
    path = event.get('path', event.get('rawPath', '/health'))
    method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method', 'GET'))
    
    if path == '/health':
        return health_handler(event, context)
    elif path == '/predict-delay' and method == 'POST':
        return predict_delay_handler(event, context)
    elif path.startswith('/route-insights/') and method == 'GET':
        return route_insights_handler(event, context)
    elif path.startswith('/booking-recommendation/') and method == 'GET':
        return booking_recommendation_handler(event, context)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': f'No handler for {method} {path}'})
        }


if __name__ == '__main__':
    # Local smoke test
    sample_event = {
        'path': '/predict-delay',
        'httpMethod': 'POST',
        'body': json.dumps({
            'airline_code': 'WN',
            'origin': 'LAX',
            'dest': 'JFK',
            'dep_hour': 18,
            'day_of_week_num': 5,
            'month_num': 6,
            'is_weekend': False,
            'distance': 2475
        })
    }
    result = lambda_handler(sample_event, {})
    print(json.dumps(json.loads(result['body']), indent=2))
