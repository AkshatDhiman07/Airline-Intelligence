"""Travel Intelligence - Delay Prediction Model Training"""

import os
import json
import time
import joblib
import boto3
import pandas as pd
import awswrangler as wr
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    roc_auc_score, classification_report,
    confusion_matrix, accuracy_score, f1_score
)

DATABASE = 'travel_intel'
SAMPLE_SIZE = 300_000
TEST_SIZE = 0.2
RANDOM_STATE = 42

LOCAL_MODEL_DIR = 'ml'
MODEL_FILE = 'delay_predictor.pkl'
COLUMNS_FILE = 'feature_columns.pkl'
METRICS_FILE = 'model_metrics.json'

S3_BUCKET = 'airline-processed-flight-data'
S3_MODEL_KEY = 'ml-models/delay_predictor_v1.pkl'
S3_COLUMNS_KEY = 'ml-models/feature_columns_v1.pkl'
S3_METRICS_KEY = 'ml-models/model_metrics_v1.json'


def fetch_training_data(sample_size):
    print(f"\n[1/5] Fetching {sample_size:,} rows from Athena...")
    start = time.time()

    query = f"""
    SELECT 
        airline_code, origin, dest, dep_hour,
        day_of_week_num, month_num, is_weekend,
        distance, delay_flag
    FROM travel_intel.flights_clean
    WHERE is_cancelled = FALSE
      AND dep_delay IS NOT NULL
      AND distance IS NOT NULL
      AND dep_hour IS NOT NULL
    ORDER BY random()
    LIMIT {sample_size}
    """

    df = wr.athena.read_sql_query(sql=query, database=DATABASE, ctas_approach=False)
    elapsed = time.time() - start
    print(f"   Fetched {len(df):,} rows in {elapsed:.1f}s")
    print(f"   Delay rate: {df['delay_flag'].mean()*100:.2f}%")
    return df


def prepare_features(df):
    print("\n[2/5] Preparing features...")
    top_origins = df['origin'].value_counts().head(30).index.tolist()
    top_dests = df['dest'].value_counts().head(30).index.tolist()
    df['origin'] = df['origin'].where(df['origin'].isin(top_origins), 'OTHER')
    df['dest'] = df['dest'].where(df['dest'].isin(top_dests), 'OTHER')

    features = ['airline_code', 'origin', 'dest', 'dep_hour',
                'day_of_week_num', 'month_num', 'is_weekend', 'distance']
    X = pd.get_dummies(df[features], columns=['airline_code', 'origin', 'dest'])
    y = df['delay_flag'].astype(int)
    print(f"   {X.shape[1]} feature columns | On-time: {sum(y==0):,} Delayed: {sum(y==1):,}")
    return X, y


def train_model(X_train, y_train):
    print("\n[3/5] Training Random Forest...")
    start = time.time()
    model = RandomForestClassifier(
        n_estimators=100, max_depth=15, min_samples_split=50,
        min_samples_leaf=20, n_jobs=-1, random_state=RANDOM_STATE,
        class_weight='balanced'
    )
    model.fit(X_train, y_train)
    print(f"   Trained in {time.time()-start:.1f}s")
    return model


def evaluate_model(model, X_test, y_test):
    print("\n[4/5] Evaluating model...")
    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probs)
    acc = accuracy_score(y_test, preds)
    f1 = f1_score(y_test, preds)
    cm = confusion_matrix(y_test, preds).tolist()

    print("=" * 60)
    print(f"AUC-ROC:   {auc:.4f}")
    print(f"Accuracy:  {acc:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(classification_report(y_test, preds, target_names=['On-time', 'Delayed']))
    print(f"Confusion Matrix: {cm}")
    print("=" * 60)

    fi = pd.DataFrame({
        'feature': X_test.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False).head(15)
    print("\nTop 15 features:")
    print(fi.to_string(index=False))

    return {
        'auc_roc': round(auc, 4),
        'accuracy': round(acc, 4),
        'f1_score': round(f1, 4),
        'confusion_matrix': cm,
        'top_features': fi.to_dict('records'),
        'model_type': 'RandomForestClassifier',
        'n_estimators': 100, 'max_depth': 15,
        'training_samples': len(X_test) * 4,
        'test_samples': len(X_test)
    }


def save_artifacts(model, feature_columns, metrics):
    print("\n[5/5] Saving artifacts...")
    os.makedirs(LOCAL_MODEL_DIR, exist_ok=True)
    local_model = os.path.join(LOCAL_MODEL_DIR, MODEL_FILE)
    local_columns = os.path.join(LOCAL_MODEL_DIR, COLUMNS_FILE)
    local_metrics = os.path.join(LOCAL_MODEL_DIR, METRICS_FILE)

    joblib.dump(model, local_model)
    joblib.dump(feature_columns, local_columns)
    with open(local_metrics, 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"   Local: {local_model} ({os.path.getsize(local_model)/1e6:.1f} MB)")

    s3 = boto3.client('s3')
    s3.upload_file(local_model, S3_BUCKET, S3_MODEL_KEY)
    s3.upload_file(local_columns, S3_BUCKET, S3_COLUMNS_KEY)
    s3.upload_file(local_metrics, S3_BUCKET, S3_METRICS_KEY)
    print(f"   S3:    s3://{S3_BUCKET}/{S3_MODEL_KEY}")


def main():
    print("=" * 60)
    print("  Travel Intelligence - Delay Prediction Training")
    print("=" * 60)

    df = fetch_training_data(SAMPLE_SIZE)
    X, y = prepare_features(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"   Train: {len(X_train):,} | Test: {len(X_test):,}")

    model = train_model(X_train, y_train)
    metrics = evaluate_model(model, X_test, y_test)
    save_artifacts(model, X.columns.tolist(), metrics)

    print("\n" + "=" * 60)
    print(f"  DONE - Model AUC: {metrics['auc_roc']}")
    print("=" * 60)


if __name__ == '__main__':
    main()

