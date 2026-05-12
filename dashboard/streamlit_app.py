"""
Travel Intelligence Dashboard
Built on Athena views + trained ML model.
"""
import streamlit as st
import pandas as pd
import awswrangler as wr
import joblib
import boto3
import plotly.express as px
from io import BytesIO

# ─────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Travel Intelligence Platform",
    page_icon="✈️",
    layout="wide"
)

DATABASE = 'travel_intel'
S3_BUCKET = 'airline-processed-flight-data'

# ─────────────────────────────────────────────────────────
# Helper: Load ML model from S3 (cached)
# ─────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    s3 = boto3.client('s3')
    model_bytes = s3.get_object(Bucket=S3_BUCKET, Key='ml-models/delay_predictor_v1.pkl')['Body'].read()
    columns_bytes = s3.get_object(Bucket=S3_BUCKET, Key='ml-models/feature_columns_v1.pkl')['Body'].read()
    model = joblib.load(BytesIO(model_bytes))
    columns = joblib.load(BytesIO(columns_bytes))
    return model, columns


# ─────────────────────────────────────────────────────────
# Helper: Run Athena queries (cached for 1 hour)
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def run_query(sql):
    return wr.athena.read_sql_query(sql=sql, database=DATABASE, ctas_approach=False)


# ─────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────
st.title("✈️ Travel Intelligence Platform")
st.markdown("**B2B Aviation Analytics** | 3M flight records | 2019-2023 | AWS-Powered")
st.markdown("---")

# ─────────────────────────────────────────────────────────
# KPI Row
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_kpis():
    df = run_query("""
        SELECT 
            COUNT(*) AS total_flights,
            ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed,
            ROUND(AVG(dep_delay), 2) AS avg_delay,
            COUNT(DISTINCT route_id) AS unique_routes
        FROM travel_intel.flights_clean
        WHERE is_cancelled = FALSE
    """)
    return df.iloc[0]

kpi = get_kpis()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Flights Analyzed", f"{int(kpi['total_flights']):,}")
col2.metric("Delay Rate (>15 min)", f"{kpi['pct_delayed']}%")
col3.metric("Avg Departure Delay", f"{kpi['avg_delay']:.1f} min")
col4.metric("Unique Routes", f"{int(kpi['unique_routes']):,}")

st.markdown("---")

# ─────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🕐 Hourly Patterns",
    "🛫 Route Analysis",
    "✈️ Airlines",
    "📉 COVID Impact",
    "🔮 Delay Predictor"
])

# ─────────────────────────────────────────────────────────
# TAB 1: Hourly Patterns
# ─────────────────────────────────────────────────────────
with tab1:
    st.header("Delay Patterns by Hour of Day")
    st.markdown("**Insight:** Morning flights are dramatically more reliable than evening flights due to delay cascading effects.")
    
    hourly = run_query("SELECT * FROM travel_intel.hourly_patterns ORDER BY dep_hour")
    
    fig = px.bar(
        hourly, x='dep_hour', y='pct_delayed_15min',
        color='time_of_day',
        labels={'dep_hour': 'Departure Hour (24h)', 'pct_delayed_15min': '% Flights Delayed >15min'},
        title="Delay Rate by Departure Hour",
        color_discrete_map={'Morning': '#2ecc71', 'Afternoon': '#f1c40f', 'Evening': '#e67e22', 'Night': '#34495e'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(hourly, use_container_width=True)


# ─────────────────────────────────────────────────────────
# TAB 2: Route Analysis
# ─────────────────────────────────────────────────────────
with tab2:
    st.header("Worst-Performing Routes")
    st.markdown("**Insight:** Use this to set traveler expectations or recommend alternative bookings.")
    
    worst_routes = run_query("""
        SELECT route_id, origin_city, dest_city, total_flights, 
               pct_delayed_15min, avg_dep_delay_min
        FROM travel_intel.route_performance
        ORDER BY pct_delayed_15min DESC
        LIMIT 20
    """)
    
    fig = px.bar(
        worst_routes.head(15), x='pct_delayed_15min', y='route_id',
        orientation='h',
        labels={'pct_delayed_15min': '% Delayed >15min', 'route_id': 'Route'},
        title="Top 15 Worst Routes",
        color='pct_delayed_15min',
        color_continuous_scale='Reds'
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(worst_routes, use_container_width=True)


# ─────────────────────────────────────────────────────────
# TAB 3: Airlines
# ─────────────────────────────────────────────────────────
with tab3:
    st.header("Airline Performance Comparison")
    
    year_filter = st.selectbox("Select year:", [2023, 2022, 2021, 2020, 2019])
    
    airlines = run_query(f"""
        SELECT airline_code, airline, total_flights, 
               pct_delayed_15min, avg_dep_delay_min,
               avg_delay_carrier, avg_delay_weather, avg_delay_nas
        FROM travel_intel.airline_performance
        WHERE year = {year_filter}
          AND total_flights > 10000
        ORDER BY pct_delayed_15min ASC
    """)
    
    fig = px.bar(
        airlines, x='airline_code', y='pct_delayed_15min',
        labels={'airline_code': 'Airline', 'pct_delayed_15min': '% Delayed >15min'},
        title=f"Airline Delay Rates ({year_filter})",
        color='pct_delayed_15min',
        color_continuous_scale='RdYlGn_r'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(airlines, use_container_width=True)


# ─────────────────────────────────────────────────────────
# TAB 4: COVID Impact
# ─────────────────────────────────────────────────────────
with tab4:
    st.header("COVID-19 Aviation Impact (2019-2023)")
    st.markdown("**Insight:** Year-over-year disruption story — pandemic, recovery, post-recovery operational chaos.")
    
    covid = run_query("SELECT * FROM travel_intel.covid_impact ORDER BY year")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        fig1 = px.line(
            covid, x='year', y='pct_delayed_15min',
            markers=True, title="% Delayed Year-over-Year",
            labels={'pct_delayed_15min': '% Flights Delayed'}
        )
        st.plotly_chart(fig1, use_container_width=True)
    
    with col_b:
        fig2 = px.bar(
            covid, x='year', y='total_flights',
            title="Total Flights Volume",
            color='total_flights', color_continuous_scale='Blues'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    st.dataframe(covid, use_container_width=True)


# ─────────────────────────────────────────────────────────
# TAB 5: ML Delay Predictor
# ─────────────────────────────────────────────────────────
with tab5:
    st.header("🔮 Real-Time Delay Prediction")
    st.markdown("**Powered by a Random Forest model trained on 300,000 flight records (AUC: 0.67)**")
    
    try:
        model, feature_columns = load_model()
        
        col_x, col_y, col_z = st.columns(3)
        with col_x:
            airline_input = st.selectbox("Airline", ['WN', 'AA', 'DL', 'UA', 'B6', 'AS', 'F9', 'NK', 'OO'])
            origin_input = st.selectbox("Origin Airport", ['ATL', 'LAX', 'ORD', 'DFW', 'DEN', 'JFK', 'SFO', 'LAS', 'SEA', 'BOS'])
            dest_input = st.selectbox("Destination Airport", ['ATL', 'LAX', 'ORD', 'DFW', 'DEN', 'JFK', 'SFO', 'LAS', 'SEA', 'BOS'])
        with col_y:
            hour_input = st.slider("Departure Hour", 0, 23, 14)
            dow_input = st.slider("Day of Week (1=Mon)", 1, 7, 3)
            month_input = st.slider("Month", 1, 12, 6)
        with col_z:
            distance_input = st.number_input("Distance (miles)", 100, 5000, 1200)
            is_weekend_input = st.checkbox("Weekend Flight", value=False)
        
        if st.button("🎯 Predict Delay Risk", type="primary"):
            input_df = pd.DataFrame([{
                'airline_code': airline_input, 'origin': origin_input, 'dest': dest_input,
                'dep_hour': hour_input, 'day_of_week_num': dow_input,
                'month_num': month_input, 'is_weekend': is_weekend_input,
                'distance': distance_input
            }])
            X = pd.get_dummies(input_df, columns=['airline_code', 'origin', 'dest'])
            X = X.reindex(columns=feature_columns, fill_value=0)
            
            prob = model.predict_proba(X)[0, 1]
            
            col_result1, col_result2 = st.columns(2)
            with col_result1:
                st.metric("Delay Probability", f"{prob*100:.1f}%")
            with col_result2:
                if prob > 0.4:
                    st.error("🔴 HIGH RISK")
                elif prob > 0.2:
                    st.warning("🟡 MEDIUM RISK")
                else:
                    st.success("🟢 LOW RISK")
            
            st.progress(min(prob, 1.0))
    except Exception as e:
        st.error(f"Could not load ML model: {e}")


# ─────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("**Architecture:** S3 Data Lake | AWS Lambda + EventBridge (live ingestion) | Athena | Random Forest ML | Streamlit")
st.markdown("**Built by:** Akshat Dhiman, Northeastern University | May 2026")
