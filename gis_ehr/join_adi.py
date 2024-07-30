# Right-join geocoded addresses with shapefile, then join with ADI table

#Imports 
import pandas as pd
import geopandas as gpd
import argparse
import os



# --- Load in MO Census Block Group shapefile ---

shp = gpd.read_file('resources/tl_2020_29_bg20.shp')
shp.rename(columns={'GEOID20':'FIPS'}, inplace=True)
shp['FIPS'] = shp['FIPS'].astype(str)

census_blocks = shp.loc[:, ['FIPS', 'geometry']]
print("Shape of census_blocks: ", census_blocks.shape)



# --- Load in address table ---

description = "Load in geocoded addresses, for ADI joining"
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

selected_columns = df.loc[:, ['location_id', 'location_x', 'location_y']]

locations_gdf = gpd.GeoDataFrame(
    selected_columns,
    geometry = gpd.points_from_xy(
        selected_columns.location_x, 
        selected_columns.location_y),
    crs = census_blocks.crs
)
print("Shape of locations_gdf: ", locations_gdf.shape)



# --- Join locations to FIPS codes ---

joined_gdf = gpd.sjoin(locations_gdf, census_blocks, how='inner', predicate='within')
joined_df = pd.DataFrame(joined_gdf[['location_id', 'FIPS']])
print("Shape of joined_df: ", joined_df.shape)

df = df.merge(joined_df, on='location_id', how='inner')



# --- Join FIPS codes to ADI metrics ---

adi_2020 = pd.read_csv('resources/MO_2020_ADI_Census_Block_Group_v4_0_1.csv')
adi_2020 = adi_2020.astype(str).rename(columns={'ADI_NATRANK':'ADI_NAT_20', 'ADI_STATERNK':'ADI_ST_20'})
df = df.merge(adi_2020, on='FIPS', how='left')

df.to_csv(
    'results/ADI_' + os.path.basename(args.infile), 
    index = False)
