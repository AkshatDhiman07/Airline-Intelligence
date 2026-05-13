# Install the Kaggle CLI
pip install kaggle

# Download the dataset
cd /tmp
kaggle datasets download -d patrickzel/flight-delay-and-cancellation-dataset-2019-2023

# Unzip it
unzip -o flight-delay-and-cancellation-dataset-2019-2023.zip

#Split the CSV by Year
mkdir -p /tmp/by_year
HEADER=$(head -1 flights_sample_3m.csv)

tail -n +2 flights_sample_3m.csv | awk -F',' -v hdr="$HEADER" '
{
  year = substr($1, 1, 4)
  outfile = "/tmp/by_year/flights_" year ".csv"
  if (!(year in seen)) {
    print hdr > outfile
    seen[year] = 1
  }
  print >> outfile
}'

#upload to s3
for f in /tmp/by_year/flights_*.csv; do
  year=$(basename "$f" .csv | sed 's/flights_//')
  aws s3 cp "$f" "s3://airline-raw-flight-data/bts/flights/year=${year}/flights.csv"
done
