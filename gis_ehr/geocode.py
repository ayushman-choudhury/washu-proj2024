# Extracted from Databricks notebook: "Ayushman - Gaia in Python"
# This code is adapted from Abigail's script

# Imports
import pandas as pd
import argparse
import os
import math
import requests

# --- Load in address table ---

# In the WUSTL Data Lake, this was:
# df = spark.sql("SELECT location_id, address_1, address_2, city as givenCity, 
# state as givenState, zip as givenZip FROM sandbox.zhang_lab.location")

description = "Geocode addresses using I2 ArcGIS server"
parser = argparse.ArgumentParser(description=description)
parser.add_argument('infile', help="path to input CSV")
args = parser.parse_args()

if not os.path.exists(args.infile) or not os.path.isfile(args.infile):
    print("ERROR: infile not found: " + args.infile)
    exit(1)

df = pd.read_csv(args.infile)

if df is None:
    print("ERROR: df is type None.")
    exit(1)

required_columns = ['location_id', 'address_1', 'address_2', 'city', 'state', 'zip']
missing_columns = [col for col in required_columns if col not in df.columns]
if missing_columns:
    print(f"ERROR: missing columns: {missing_columns}")
    exit(1)
    
df.rename(columns={
    'city': 'givenCity', 
    'state': 'givenState', 
    'zip': 'givenZip'}, inplace=True)

# The ArcGIS server has a batch limit of 1000 addresses
ADDRESSES_PER_BATCH = 1000 
NROW = df.shape[0]
BATCH_NUMS = math.ceil(NROW / ADDRESSES_PER_BATCH)
global_geocodes = []

print(f"There are {NROW} rows")
print(f"These will be processed in {BATCH_NUMS} batches.")

# --- Helper: manually parse combining address_1 and address_2 --- 

def combine_address(add1, add2):
    # Evaluate none-types
    if pd.isna(add1) and pd.isna(add2):
        return ""
    elif pd.isna(add1):
        return add2
    elif pd.isna(add2):
        return add1
    # Evaluate equality and substrings
    add1, add2 = add1.strip(), add2.strip()
    if add1 == add2:
        return add1
    elif add1 in add2:
        return add2
    elif add2 in add1:
        return add1
    # If add2 starts with a digit, put it first
    if add2 and add2[0].isdigit():
        return add2 + " " + add1
    # Default: add1 + add2
    return add1 + " " + add2



# --- Geocoding helper functions ---
def formatRecords(data):
    records = []
    for index, row in data.iterrows():
        attributes = dict({"ObjectID" : row["location_id"], 
                           "address" : row["street_address"], 
                           "city" : row["givenCity"], 
                           "region" : row["givenState"], 
                           "postal" : row["givenZip"]})
        records.append(dict({"attributes": attributes}))
    return dict({"records" : records})

def sendPostRequest(records):
    url = "https://10.25.44.136:6443/arcgis/rest/services/USA/GeocodeServer/geocodeAddresses"
    params = {"f" : "pjson", "addresses" : str(records)}
    result = requests.post(url, data = params, verify = False)
    return result.json()

def parsePostResponse(response):
    locations = response["locations"]
    d = []
    for l in locations:
        location_id = l["attributes"].get("ResultID", None)
        address = l.get("address", None)
        location_x = l.get("location", {}).get("x", None)
        location_y = l.get("location", {}).get("y", None)
        score = l.get("score", None)
        status = l["attributes"].get("Status", None)
        d.append((location_id, address, location_x, location_y, score, status))
    return d

def driver(i): 
    global global_geocodes

    # Define the batch
    startBatch = i * ADDRESSES_PER_BATCH
    endBatch = min(NROW, startBatch + ADDRESSES_PER_BATCH)
    data_batch = df[startBatch:endBatch]
    print("\n\nBatch:", startBatch + 1, "-", endBatch, "of", NROW)
    
    # Geocode the batch
    print("Formatting records...")
    records = formatRecords(data_batch)
    print("Sending request...")
    response = sendPostRequest(records)
    del(records)
    print("Parsing request...")
    geocoding_results = parsePostResponse(response)
    del(response)
    
    # Save results
    if len(global_geocodes) == 0:
        global_geocodes = geocoding_results
    else:
        global_geocodes = global_geocodes + geocoding_results



# --- Call all functions ---
df['street_address'] = df.apply(lambda row: combine_address(row['address_1'], row['address_2']), axis=1)

for i in range(0, BATCH_NUMS):
    driver(i)

geocoded_df = pd.DataFrame(global_geocodes,
    columns=['location_id', 'matched_address', 'location_x', 'location_y', 'score', 'status']
)

merged_df = pd.merge(df, geocoded_df, on='location_id', how='left')

merged_df.to_csv(
    'results/GEOCODED_' + os.path.basename(args.infile), 
    index = False)
