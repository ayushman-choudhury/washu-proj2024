# GIS EHR Integration

EHR (Electronic Health Records) is stored in WUSTL's data lake, run on Databricks. 
GIS (Geographic Information Systems) refers in this context to any spatial data. Coordinates for scatterplots, distances, summarization into census regions (tracts, blocks, etc.), and metrics related to those regions are all geographic data.
This project seeks to integrate EHR and GIS, so that we can conduct various kinds of spatial analysis. 

## Environment
- File-managing packages: `argparse`, `os`
- HTTP package (for ArcGIS API calls): `requests`
- Numerical packages: `math`, `pandas`, `geopandas`

## Outline of Terminal Instructions
```
python geocode.py FILENAME.CSV
python join_adi.py results/GEOCODED_FILENAME.CSV
python plot_adi.py results/ADI_GEOCODED_FILENAME.CSV
```



## geocode.py

I have already geocoded all addresses in sandbox.zhang_lab.location, the results of which can be found in sandbox.zhang_lab.location_geocoded. I did this in a Databricks notebook inside the WUSTL cloud infrastructure. 

I extracted the relevant code to geocode.py, for documentation purposes. Since it is no longer within the data lake, if you wish to test out the script, you must input a CSV of our choice to geocode. Simply run the command:

```
python geocode.py [filename.csv]
```

When exported from the cloud, the input CSV will have these 6 columns:
- location_id
- address_1 
- address_2
- city
- state
- zip

Technically the address fields can be empty, but this impacts the accuracy of the geocoding process. 

The script will output a CSV to the `results` subfolder. It will contain all input columns, and:
- matched_address (the closest match for the input address the geocoder could find)
- location_x (the x-coordinate of the matched address)
- location_y (the y-coordinate)
- score (ArcGIS's score, 0-100, of its algorithm for this row)
- status (returned by ArcGIS, not used in my analysis)

Again, if you have access to the WUSTL data lake, this script (in a slightly different form) has already been run on every single address in sandbox.zhang_lab.location. The output can be found in sandbox.zhang_lab.location_geocoded.

## join_adi.py

The [Area Deprivation Index](https://www.neighborhoodatlas.medicine.wisc.edu/) is a metric created by the University of Wisconsin's Neighborhood Atlas. It measures a Census Block Group's socio-economic deprivation on a national scale (1 - 100) and a state scale (1-10), where a low score implies less neighborhood deprivation, and a high score implies more neighborhood deprivation. Anyone can use the link above to create a free account and download the data. I downloaded MO 2020 data, which is in the `resources` subfolder. 

The data labels each Census Block Group using its FIPS (Federal Information Processing System) code. However, we need the boundaries of each FIPS code. This comes from a .shp file ("shapefile"), which includes a dataframe where each row contains (among other things) a FIPS code, and a Polygon outlining the boundary of that region. This file can be downloaded from the [US Census website](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.2020.html#list-tab-790442341); I downloaded MO 2020 data, and stored the 2020 BG (block group) files in the same `resources` subfolder.

The strategy is this:
- Match each address to a particular FIPS code that defines a Census Block Group
    - In mathematical terms, find the Polygon in the shapefile that contains the (x,y) coordinate
- Match each address's FIPS code to an ADI National score and ADI State score.


Since I have only downloaded the files related to Missouri in 2020, if you want to look at other states, or other times, you will need to download more files at the linked websites. My script works specifically for Missouri addresses.

Simply run the command:

```
python join_adi.py [GEOCODED_filename.csv]
```

The input CSV is ideally the output CSV of the previous step, found in `results`. If not, ensure that it has these columns:
- location_id
- location_x
- location_y

The script will output a CSV to `results` with all columns of the input CSV, and:
- FIPS
- GISJOIN
- ADI_NAT_20
- ADI_ST_20


## plot_adi.py

Spatial data lends itself well to visualization. We can make:
- scatterplots (each dot is a location coordinate, potentially colored by some variable)
- choropleths (each region is a Polygon, colored by some variable)

Simply run the command:

```
python plot_adi.py [ADI_GEOCODED_filename.csv]
```


The input CSV must have columns:
- a
- b
- c

The script will output a PDF (dpi 300) with all the plots.

