import sys
import os
import shutil
import re
import pandas as pd
import requests
import urllib3
import argparse
import math

# import debugger
import pdb
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
########################################################################################################################
# Command line argument parsing
########################################################################################################################


description = "Geocode addresses using I2 ArcGIS server"
 
# initialize the parser
parser = argparse.ArgumentParser(description=description)
 
# generic arguments
parser.add_argument("infile",
                    help="path to csv file with addresses to geocode")
                   
parser.add_argument("-d", "--delimiter",
                    help="delimiter of the input file",
                    default=",")
 
parser.add_argument("-s", "--singleLine",
                    action="store_true",
                    help="addresses are in a single column called address")
                   
parser.add_argument("-v", "--validate",
                    action="store_true",
                    help="filter out invalid addresses (e.g. UNKNOWN, PO BOX, etc)")
 
# output arguments
parser.add_argument("-o", "--outputPath",
                    default=".",
                    help="directory to store output")
 
args = parser.parse_args()



########################################################################################################################
# Check arguments
########################################################################################################################
 
# infile
if not os.path.exists(args.infile) or not os.path.isfile(args.infile):
    print("ERROR: infile not found: " + args.infile)
    exit(1)
 
# output directory
if not os.path.exists(args.outputPath):
    os.makedirs(args.outputPath)
 
 
########################################################################################################################
# Functions for geocoding
########################################################################################################################
 


########################################################################################################################
# Choose which addresses to include in the visualization based on their states
# Only called if there is no -s (for single line), but there is a -v (for validate)

#STATES_OF_INTEREST = ["MISSOURI", "ILLINOIS"]
# Non Missouri or Illinois States
STATES_OF_INTEREST = ["MISSOURI", "ILLINOIS","ALABAMA","ALASKA","ARIZONA","ARKANSAS","CALIFORNIA","COLORADO", "CONNECTICUT","DELAWARE","FLORIDA","GEORGIA","INDIANA","IOWA","KANSAS","KENTUCKY","LOUISIANA","MARYLAND","MASSACHUSETTS", "MICHIGAN", "MINNESOTA","MISSISSIPPI","NEBRASKA","NEVADA","NEW JERSEY","NEW MEXICO", "NEW YORK","NORTH CAROLINA", "OHIO","OKLAHOMA","OREGON" , "PENNSYLVANIA","RHODE ISLAND","TENNESSEE","TEXAS","UTAH","VIRGINIA" ,"WASHINGTON","WISCONSIN" ]
NA_VALUES = ["", "N/A", "NA"]
SINGLE_LINE_ADDRESS_FIELD = "address"
ADDRESS_FIELDS = ["ADD_LINE_1", "ADD_LINE_2", "CITY", "STATE", "ZIP"]
 
def is_input_valid_result_address(x):
    [add1, add2, city, state, zip] = x[ADDRESS_FIELDS].str.upper()
    if state not in STATES_OF_INTEREST:
        return False
    if add1 in NA_VALUES and add2 in NA_VALUES:
        return False
    if re.match(".*UNKNOWN.*", add1) or re.match(".*UNKNOWN.*", add2):
        return False
    if re.match(".*UPDATE.*", add1) or re.match(".*UPDATE.*", add2):
        return False
    if (re.match("^PO BOX \d+$", add1) and add2 in NA_VALUES) or (re.match("^PO BOX \d+$", add2) and add1 in NA_VALUES):
        return False
    return True
########################################################################################################################





def sendPostRequest(records):
    ## Original url
    ##url = https://10.25.63.131:6443/arcgis/rest/services/USA_StreetAddress_StreetName_Point/GeocodeServer/geocodeAddresses
    url = "https://10.25.44.136:6443/arcgis/rest/services/USA/GeocodeServer/geocodeAddresses"
    ## Ian sent us the url that ends with "findAddressCandidates" instead of "geocodeAddresses"
    params = {"f" : "pjson", "addresses" : str(records)}
    result = requests.post(url, data = params, verify = False)
    return result.json()
 
def parsePostResponse(response):
    try:
        print(response['error'])
        sys.exit(-100)
    except:
        pass
    locations = response["locations"]
    
    # Edit below data to consider Null data
    #d = [[l["attributes"]["ResultID"], l["address"], l["location"]["x"], l["location"]["y"], l["score"], l["attributes"]["Status"]] for l in locations]
    
    d = []
    for l in locations:
        result_id = l["attributes"].get("ResultID", None)
        address = l.get("address", None)
        location_x = l.get("location", {}).get("x", None)
        location_y = l.get("location", {}).get("y", None)
        score = l.get("score", None)
        status = l["attributes"].get("Status", None)
        d.append([result_id, address, location_x, location_y, score, status])

    df = pd.DataFrame(d, columns = ("ID", "Returned Address", "Longitude", "Latitude", "Score", "Status"))
    df = df.sort_values("ID")
    return df
 
def formatRecordsSingleLine(data):
    print("... using single-line formatter")
    #pdb.set_trace()
    #print(data.columns)
    addresses = data['address']
    records = []
    for i, address in enumerate(addresses):
        attributes = dict({"ObjectID" : i, "SingleLine" : address})
        records.append(dict({"attributes": attributes}))
    return dict({"records" : records})
 
def formatRecords(data):
    print("... using multi-line formatter")
    records = []
    i = 0
    for index, row in data.iterrows():
        attributes = dict({"ObjectID" : i, 
                           "address" : row["street_address"], 
                           "city" : row["givenCity"], 
                           "region" : row["givenState"], 
                           "postal" : row["givenZip"]})
        records.append(dict({"attributes": attributes}))
        i+=1
    return dict({"records" : records})
 
def geocode(data, singleLine):
    records = formatRecordsSingleLine(data) if singleLine else formatRecords(data)
    print("Sending Request...")
    response = sendPostRequest(records)
    print("... request received!")
    geocoded_addresses = parsePostResponse(response)
    return geocoded_addresses
 
########################################################################################################################
# Read data
########################################################################################################################

#data = pd.read_csv(args.infile , dtype=str, header=0, index_col=0, keep_default_na=False, sep=args.delimiter)
data = pd.read_csv(args.infile , dtype=str, header=0, keep_default_na=False, sep=args.delimiter)
data = data.replace("N/A","")
# data = data[0:250]
print("Rows in file:", len(data.index))
print("Columns in file:", data.columns)
 
# filter for valid addresses if they are in separate fields. Assume a single line address is valid
if not args.singleLine and args.validate:
    data = data[data.apply(is_input_valid_result_address, axis=1)]
    print("Valid input addresses:", len(data.index))
 
########################################################################################################################
# Geocoding
########################################################################################################################
 
# Instead of doing this, just require input data to be well-formatted.
# Create street address
#if not args.singleLine:
   #data["STREET"] = data.apply(lambda row: " ".join(row[["ADD_LINE_1", "ADD_LINE_2"]]), axis = 1)
    #data["STREET"] = data["ADD_LINE_1"]
    #data['ZIP'] = data['ZIP'].astype(str)
    #data['ZIP'] = data["ZIP"].str.extract('(\d+)', expand=False).astype(str).str.zfill(5)
   
output_columns = ["Returned Address", "Latitude", "Longitude", "Score", "Status"]

# add output columns
for col in output_columns:
    #data = data.assign(**{col:""})
    if col not in data.columns:
        data[col] = ""

 
# The ArcGIS server has a batch limit of 1000 addresses
ADDRESSES_PER_BATCH = 1000
for i in range(0, math.ceil(data.shape[0] / ADDRESSES_PER_BATCH)):
    startBatch = i * ADDRESSES_PER_BATCH
    endBatch = min(data.shape[0], startBatch + ADDRESSES_PER_BATCH)
    data_batch = data[startBatch:endBatch]
   
    print("Geocoding rows", startBatch+1, "-", endBatch)
 
    geocoding_results = geocode(data_batch, args.singleLine)
   
    for col in output_columns:
        data.iloc[startBatch:endBatch, data.columns.get_loc(col)] = geocoding_results[col].values
 
########################################################################################################################
# Output
########################################################################################################################
#data = data.drop(columns=['STREET'])

#data = data.sort_values(by='Score', ascending=True) if 'Score' in data.columns

# Previously - tsv
#[tmp_file_name, tmp_file_ext] = os.path.splitext(os.path.basename(args.infile))
#tmp_file_path = os.path.join(args.outputPath, tmp_file_name + "_GEOCODED.tsv")
#data.to_csv(tmp_file_path, sep="\t")

# csv
method = "_single" if args.singleLine else "_multi"
[tmp_file_name, tmp_file_ext] = os.path.splitext(os.path.basename(args.infile))
tmp_file_path = os.path.join(args.outputPath, tmp_file_name + method + "_GEOCODED.csv")
data.to_csv(tmp_file_path, sep=",")