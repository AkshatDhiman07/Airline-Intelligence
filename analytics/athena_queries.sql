-- ============================================================
-- Travel Intelligence Platform - Athena Queries
-- ============================================================
-- Database: travel_intel
-- Source: s3://airline-raw-flight-data/bts/flights/ (CSV, partitioned by year)
-- ============================================================


-- 1. Create database
-- ============================================================
CREATE DATABASE IF NOT EXISTS travel_intel
COMMENT 'Travel Intelligence MVP - flight data warehouse';


-- 2. External table: flights (3M rows, 2019-2023)
-- ============================================================
CREATE EXTERNAL TABLE IF NOT EXISTS travel_intel.flights (
    fl_date                    STRING,
    airline                    STRING,
    airline_dot                STRING,
    airline_code               STRING,
    dot_code                   STRING,
    fl_number                  STRING,
    origin                     STRING,
    origin_city                STRING,
    dest                       STRING,
    dest_city                  STRING,
    crs_dep_time               INT,
    dep_time                   DOUBLE,
    dep_delay                  DOUBLE,
    taxi_out                   DOUBLE,
    wheels_off                 DOUBLE,
    wheels_on                  DOUBLE,
    taxi_in                    DOUBLE,
    crs_arr_time               INT,
    arr_time                   DOUBLE,
    arr_delay                  DOUBLE,
    cancelled                  DOUBLE,
    cancellation_code          STRING,
    diverted                   DOUBLE,
    crs_elapsed_time           DOUBLE,
    elapsed_time               DOUBLE,
    air_time                   DOUBLE,
    distance                   DOUBLE,
    delay_due_carrier          DOUBLE,
    delay_due_weather          DOUBLE,
    delay_due_nas              DOUBLE,
    delay_due_security         DOUBLE,
    delay_due_late_aircraft    DOUBLE
)
PARTITIONED BY (year INT)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar'     = '"',
    'escapeChar'    = '\\'
)
STORED AS TEXTFILE
LOCATION 's3://airline-raw-flight-data/bts/flights/'
TBLPROPERTIES (
    'skip.header.line.count'     = '1',
    'has_encrypted_data'         = 'false',
    'use.null.for.invalid.data'  = 'true'
);

MSCK REPAIR TABLE travel_intel.flights;


-- 3. View: flights_clean (cleaning + feature engineering)
-- ============================================================
CREATE OR REPLACE VIEW travel_intel.flights_clean AS
SELECT
    fl_date,
    CAST(fl_date AS DATE) AS flight_date,
    year,
    airline,
    airline_code,
    fl_number,
    origin,
    origin_city,
    dest,
    dest_city,
    origin || '-' || dest AS route_id,
    distance,
    crs_dep_time,
    CAST(crs_dep_time / 100 AS INT) AS dep_hour,
    CASE 
        WHEN CAST(crs_dep_time / 100 AS INT) BETWEEN 5  AND 11 THEN 'Morning'
        WHEN CAST(crs_dep_time / 100 AS INT) BETWEEN 12 AND 16 THEN 'Afternoon'
        WHEN CAST(crs_dep_time / 100 AS INT) BETWEEN 17 AND 20 THEN 'Evening'
        ELSE 'Night'
    END AS time_of_day,
    day_of_week(CAST(fl_date AS DATE)) AS day_of_week_num,
    CASE day_of_week(CAST(fl_date AS DATE))
        WHEN 1 THEN 'Mon' WHEN 2 THEN 'Tue' WHEN 3 THEN 'Wed'
        WHEN 4 THEN 'Thu' WHEN 5 THEN 'Fri' WHEN 6 THEN 'Sat'
        WHEN 7 THEN 'Sun'
    END AS day_of_week,
    CASE WHEN day_of_week(CAST(fl_date AS DATE)) IN (6, 7) THEN TRUE ELSE FALSE END AS is_weekend,
    month(CAST(fl_date AS DATE)) AS month_num,
    dep_delay,
    arr_delay,
    CASE WHEN dep_delay > 15 THEN 1 ELSE 0 END AS delay_flag,
    CASE 
        WHEN dep_delay IS NULL THEN 'Unknown'
        WHEN dep_delay <= 0    THEN 'On-time/Early'
        WHEN dep_delay <= 15   THEN 'Minor (1-15min)'
        WHEN dep_delay <= 60   THEN 'Moderate (16-60min)'
        WHEN dep_delay <= 180  THEN 'Major (1-3hr)'
        ELSE 'Severe (3hr+)'
    END AS delay_category,
    CASE WHEN cancelled = 1.0 THEN TRUE ELSE FALSE END AS is_cancelled,
    CASE WHEN diverted = 1.0  THEN TRUE ELSE FALSE END AS is_diverted,
    cancellation_code,
    delay_due_carrier,
    delay_due_weather,
    delay_due_nas,
    delay_due_security,
    delay_due_late_aircraft,
    taxi_out,
    taxi_in,
    air_time,
    elapsed_time,
    crs_elapsed_time
FROM travel_intel.flights
WHERE fl_date IS NOT NULL
  AND origin  IS NOT NULL
  AND dest    IS NOT NULL
  AND crs_dep_time IS NOT NULL;


-- 4. Analytics View: route_performance
-- ============================================================
CREATE OR REPLACE VIEW travel_intel.route_performance AS
SELECT 
    route_id,
    origin,
    dest,
    origin_city,
    dest_city,
    COUNT(*) AS total_flights,
    ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed_15min,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_min,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_min,
    ROUND(AVG(distance), 0) AS avg_distance_miles
FROM travel_intel.flights_clean
WHERE is_cancelled = FALSE
GROUP BY route_id, origin, dest, origin_city, dest_city
HAVING COUNT(*) > 1000;


-- 5. Analytics View: airline_performance
-- ============================================================
CREATE OR REPLACE VIEW travel_intel.airline_performance AS
SELECT 
    airline_code,
    airline,
    year,
    COUNT(*) AS total_flights,
    ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed_15min,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_min,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_min,
    ROUND(AVG(delay_due_carrier), 2) AS avg_delay_carrier,
    ROUND(AVG(delay_due_weather), 2) AS avg_delay_weather,
    ROUND(AVG(delay_due_nas), 2) AS avg_delay_nas,
    ROUND(AVG(delay_due_late_aircraft), 2) AS avg_delay_late_aircraft
FROM travel_intel.flights_clean
WHERE is_cancelled = FALSE
GROUP BY airline_code, airline, year;


-- 6. Analytics View: hourly_patterns
-- ============================================================
CREATE OR REPLACE VIEW travel_intel.hourly_patterns AS
SELECT 
    dep_hour,
    time_of_day,
    COUNT(*) AS total_flights,
    ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed_15min,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_min,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_min
FROM travel_intel.flights_clean
WHERE is_cancelled = FALSE
  AND dep_hour BETWEEN 0 AND 23
GROUP BY dep_hour, time_of_day;


-- 7. Analytics View: covid_impact
-- ============================================================
CREATE OR REPLACE VIEW travel_intel.covid_impact AS
SELECT 
    year,
    COUNT(*) AS total_flights,
    ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed_15min,
    ROUND(AVG(dep_delay), 2) AS avg_dep_delay_min,
    ROUND(AVG(arr_delay), 2) AS avg_arr_delay_min,
    ROUND(AVG(delay_due_carrier), 2) AS avg_carrier_delay,
    ROUND(AVG(delay_due_weather), 2) AS avg_weather_delay,
    ROUND(AVG(delay_due_nas), 2) AS avg_nas_delay,
    ROUND(AVG(delay_due_late_aircraft), 2) AS avg_late_aircraft_delay
FROM travel_intel.flights_clean
GROUP BY year
ORDER BY year;


-- ============================================================
-- BUSINESS INTELLIGENCE QUERIES (used by dashboard)
-- ============================================================

-- Q1: KPIs for dashboard header
SELECT 
    COUNT(*) AS total_flights,
    ROUND(AVG(CAST(delay_flag AS DOUBLE)) * 100, 2) AS pct_delayed,
    ROUND(AVG(dep_delay), 2) AS avg_delay,
    COUNT(DISTINCT route_id) AS unique_routes
FROM travel_intel.flights_clean
WHERE is_cancelled = FALSE;


-- Q2: Worst 20 routes by delay rate
SELECT route_id, origin_city, dest_city, total_flights, 
       pct_delayed_15min, avg_dep_delay_min
FROM travel_intel.route_performance
ORDER BY pct_delayed_15min DESC
LIMIT 20;


-- Q3: Best airlines in 2023 (most reliable)
SELECT airline_code, airline, total_flights, pct_delayed_15min, avg_dep_delay_min
FROM travel_intel.airline_performance
WHERE year = 2023
  AND total_flights > 10000
ORDER BY pct_delayed_15min ASC
LIMIT 10;


-- Q4: Hourly delay patterns (THE money chart)
SELECT * FROM travel_intel.hourly_patterns ORDER BY dep_hour;


-- Q5: COVID impact (year-over-year)
SELECT * FROM travel_intel.covid_impact;
