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
        colorscale='Viridis'  # Adjust colorscale as needed
    )
))

scatterPlot.update_layout(
    title='Addresses, colored by ADI_NAT_20 (Black if NA)',
    geo_scope='usa'
)


# UNCOMMENT LATER
#scatterPlot.write_image('TESTScatterplot.png')



# --- Load in MO Census Block Group shapefile ---


shp = gpd.read_file('resources/tl_2020_29_bg20.shp')
shp.rename(columns={'GEOID20':'FIPS'}, inplace=True)
census_blocks = shp.loc[:, ['FIPS', 'geometry']]
census_blocks['FIPS'] = census_blocks['FIPS'].astype(str)



# --- Merge geometries with data ---

df_filtered = df[~pd.isna(df['ADI_NAT_20'])]

x_range = max(df_filtered['location_x']) - min(df_filtered['location_x'])
x_window = [min(df_filtered['location_x']) - 0.01 - x_range/2, 
            max(df_filtered['location_x']) + 0.01 + x_range/2]
y_range = max(df_filtered['location_y']) - min(df_filtered['location_y'])
y_window = [min(df_filtered['location_y']) - 0.01 - y_range/2, 
            max(df_filtered['location_y']) + 0.01 + y_range/2]
window = [x_window, y_window]

fips_summary = df.groupby(['FIPS', 'ADI_NAT_20', 'ADI_ST_20']).size().reset_index(name='Count')
fips_summary['FIPS'] = fips_summary['FIPS'].astype(int).astype(str)

merged_df = fips_summary.merge(census_blocks, on='FIPS')

merged_gdf = gpd.GeoDataFrame(merged_df, crs=census_blocks.crs)
print(merged_gdf)
print(type(merged_gdf))



# --- Count choropleth plot ---

fig, axs = plt.subplots(1, 1)

ax_count = axs
ax_count.set_title("Counts by Census Block Group")
ax_count.set_xlim(x_window)
ax_count.set_ylim(y_window)
merged_gdf.plot(column='Count', edgecolor='black', legend=True, ax=ax_count)

#plt.savefig('TESTchoropleth.png')



# --- ADI choropleth plot ---
merged_gdf['ADI_NAT_20_numeric'] = pd.to_numeric(merged_gdf['ADI_NAT_20'], errors='coerce')
adiNum_merged_gdf = merged_gdf[merged_gdf['ADI_NAT_20_numeric'].notna()]
adiString_merged_gdf = merged_gdf[merged_gdf['ADI_NAT_20_numeric'].isna()]

print(adiNum_merged_gdf)
print(adiString_merged_gdf)