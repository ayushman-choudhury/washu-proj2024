# Make plots using an ADI_GEOCODED file.

#Imports
import argparse
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import plotly.graph_objects as go
import matplotlib.pyplot as plt


# --- Load in csv ---

description = "Plot addresses and ADI metrics spatially"
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


# --- Scatterplot of data ---

def convert_adi(adi):
    try:
        return float(adi)
    except ValueError:
        return np.nan

df['ADI_NAT_20_numeric'] = df['ADI_NAT_20'].apply(convert_adi)
colors = ['black' if pd.isna(adi) else adi for adi in df['ADI_NAT_20_numeric']]

# Create scatter plot
scatterPlot = go.Figure(data=go.Scattergeo(
    lon = df['location_x'],
    lat = df['location_y'],
    mode = 'markers',
    marker = dict(
        line = dict(width=1, color='rgba(0, 0, 0)'),
        color = colors,
        colorbar_title="ADI_NAT_20",
    )
))

scatterPlot.update_layout(
    title='Addresses, colored by ADI_NAT_20 (Black if NA)',
    geo_scope='usa'
)

scatterPlot.write_image('results/scatterplot.png')



# --- Load in and merge MO Census Block Group shapefile ---

shp = gpd.read_file('resources/tl_2020_29_bg20.shp')
shp.rename(columns={'GEOID20':'FIPS'}, inplace=True)
census_blocks = shp.loc[:, ['FIPS', 'geometry']]
census_blocks['FIPS'] = census_blocks['FIPS'].astype(str)

df_filtered = df[~pd.isna(df['ADI_NAT_20'])]

# Establish generous window for later plots
x_range = max(df_filtered['location_x']) - min(df_filtered['location_x'])
x_window = [min(df_filtered['location_x']) - 0.01 - x_range/2, 
            max(df_filtered['location_x']) + 0.01 + x_range/2]
y_range = max(df_filtered['location_y']) - min(df_filtered['location_y'])
y_window = [min(df_filtered['location_y']) - 0.01 - y_range/2, 
            max(df_filtered['location_y']) + 0.01 + y_range/2]
window = [x_window, y_window]

# Groupby to get counts
fips_summary = df.groupby(['FIPS', 'ADI_NAT_20', 'ADI_ST_20']).size().reset_index(name='Count')
fips_summary['FIPS'] = fips_summary['FIPS'].astype(int).astype(str)

merged_df = fips_summary.merge(census_blocks, on='FIPS')

merged_gdf = gpd.GeoDataFrame(merged_df, crs=census_blocks.crs)

# Separate ADI numeric and string error codes
merged_gdf['ADI_NAT_20_numeric'] = pd.to_numeric(merged_gdf['ADI_NAT_20'], errors='coerce')
adiNum_merged_gdf = merged_gdf[merged_gdf['ADI_NAT_20_numeric'].notna()]
adiString_merged_gdf = merged_gdf[merged_gdf['ADI_NAT_20_numeric'].isna()]



# --- Choropleth plots ---

plt.figure(figsize=[10,5])
fig, axs = plt.subplots(2, 2)

# Count
ax_count = axs[0,0]
ax_count.set_title("Counts by CBG")
ax_count.set_xlim(x_window)
ax_count.set_ylim(y_window)
merged_gdf.plot(column='Count', edgecolor='black', legend=True, ax=ax_count)

# Blank
axs[0, 1].axis('off')

# ADI numeric
ax_adiNum = axs[1,0]
ax_adiNum.set_title("ADI (Numeric) by CBG")
ax_adiNum.set_xlim(x_window)
ax_adiNum.set_ylim(y_window)
adiNum_merged_gdf.plot(column='ADI_NAT_20_numeric', edgecolor='black', legend=True, ax=ax_adiNum)


# ADI string errors
ax_adiStr = axs[1,1]
ax_adiStr.set_title("ADI Errors")
ax_adiStr.set_xlim(x_window)
ax_adiStr.set_ylim(y_window)
adiString_merged_gdf.plot(column='ADI_NAT_20', edgecolor='black', legend=True, ax=ax_adiStr)

plt.tight_layout()
plt.savefig('results/choroplethPlots.png')