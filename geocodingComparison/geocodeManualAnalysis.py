import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Define files to analyze
ARCFILES = ['arcgisGeocode/stratumA_single_GEOCODED.csv', 
         'arcgisGeocode/stratumA_multi_GEOCODED.csv',
         'arcgisGeocode/stratumB_single_GEOCODED.csv', 
         'arcgisGeocode/stratumB_multi_GEOCODED.csv']

DGFILES = ['degauss/stratumA_geocoder_3.3.0_score_threshold_0.5.csv',
           'degauss/stratumB_geocoder_3.3.0_score_threshold_0.5.csv']

STRATUMA = ['arcgisGeocode/stratumA_single_GEOCODED.csv', 
            'arcgisGeocode/stratumA_multi_GEOCODED.csv',
            'degauss/stratumA_geocoder_3.3.0_score_threshold_0.5.csv']

STRATUMB = ['arcgisGeocode/stratumB_single_GEOCODED.csv', 
            'arcgisGeocode/stratumB_multi_GEOCODED.csv',
            'degauss/stratumB_geocoder_3.3.0_score_threshold_0.5.csv']

PLOTFILES = ['arcgisGeocode/stratumA_multi_GEOCODED.csv',
             'degauss/stratumA_geocoder_3.3.0_score_threshold_0.5.csv',
             'arcgisGeocode/stratumB_multi_GEOCODED.csv',
           'degauss/stratumB_geocoder_3.3.0_score_threshold_0.5.csv']

FLAGGED_ADDRESSES = set()


def get_scores_from_csv(filename):
    
    # Read the CSV file
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print("No data in file.")
        sys.exit(1)
    except pd.errors.ParserError:
        print("Error parsing the file.")
        sys.exit(1)

    # Check if the 'score' column exists
    if 'score' in df.columns:
        scores = df['score']
    elif 'Score' in df.columns:
        scores = df['Score']
    else:
        print("'score' column not found in the CSV file.")
        sys.exit(1)

    # Multiplication factor to scale scores
    factor = 0.01 if scores.max() > 1 else 1
    scores = scores * factor

    return {
        "filename": filename,
        "scores": scores.values
    }

    # # Calculate the 5-number summary
    # score_summary = scores.describe(percentiles=[.25, .5, .75])

    # return {
    #     "filename": filename,
    #     "min": score_summary['min'],
    #     "25%": score_summary['25%'],
    #     "50% (Median)": score_summary['50%'],
    #     "75%": score_summary['75%'],
    #     "max": score_summary['max'],
    #     "mean": scores.mean(),
    #     "scores_below_90": len(scores[scores < 0.9])
    # }





def matchCityStateZip(filename):
    
    # Read the CSV file
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print("No data in file.")
        sys.exit(1)
    except pd.errors.ParserError:
        print("Error parsing the file.")
        sys.exit(1)

    # Get the given columns and matched columns
    givenCols = df[['address', 'givenCity', 'givenState', 'givenZip']].astype('str')

    if filename in ARCFILES:
        addr = df['Returned Address']
        regex = r'(?P<matched_city>[^,]+),\s*(?P<matched_state>[A-Za-z\s]+),\s*(?P<matched_zip>\d{5})'
        matchedCols = addr.str.extract(regex).astype(str)
    if filename in DGFILES:
        matchedCols = df[['matched_city', 'matched_state', 'matched_zip']].astype('str')

    # Check equality
    citiesEqual = []
    zipsEqual = []
    zipsNan = []
    zipsDiff = []
    mismatchTable = []
    for i in range(len(givenCols)):
        # Get the data
        givenCity = givenCols.loc[i]['givenCity'].lower().strip()
        givenZip = givenCols.loc[i]['givenZip'][0:5]
        matchedCity = matchedCols.loc[i]['matched_city'].lower().strip()
        matchedZip = matchedCols.loc[i]['matched_zip'][0:5]

        if len(matchedZip) == 5 and matchedZip[4] == '.':
            matchedZip = '0' + matchedZip[:4]
        
        # Calculate booleans
        cityEqual = givenCity == matchedCity
        zipEqual = givenZip == matchedZip
        zipNan = matchedZip == 'nan'
        zipDiff = not (zipEqual or zipNan)
        
        # Put them in vectors
        citiesEqual.append(cityEqual)
        zipsEqual.append(zipEqual)
        zipsNan.append(zipNan)
        zipsDiff.append(zipDiff)

        # If Zip codes aren't equal, flag the address
        if (not zipEqual):
            
            FLAGGED_ADDRESSES.add(givenCols.loc[i]['address'])

            # May remove the mismatchDict importance
            if 'single' in filename:
                fileType = "arcGISsingle"
            elif 'multi' in filename:
                fileType = "arcGISmulti"
            else:
                fileType = "DeGAUSS"
            
            mismatchDict = {
                "address": givenCols.loc[i]['address'],
                "givenCity": givenCity,
                "givenZip": givenZip,
                "matchedCity_"+fileType: matchedCity,
                "matchedZip_"+fileType: matchedZip
            }

            mismatchTable.append(mismatchDict)

    # Return results:
    matchDict = {
        "filename": filename,
        "cityMatch": sum(citiesEqual),
        "zipCodeMatch": sum(zipsEqual),
        "Nan zip codes": sum(zipsNan),
        "Diff zip codes": sum(zipsDiff)
    }

    return matchDict, mismatchTable




def getFlaggedRows(filename):
    
    # Read the CSV file
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        print("No data in file.")
        sys.exit(1)
    except pd.errors.ParserError:
        print("Error parsing the file.")
        sys.exit(1)
    
    # If the address is in FLAGGED_ADDRESSES, get the data
    address_column_index = df.columns.get_loc('address')
    flagged_rows = df[df['address'].isin(FLAGGED_ADDRESSES)].iloc[:, address_column_index:].sort_values(by='address')
    
    return flagged_rows



#############
plotLabels = ['arcGIS - stratum A', 'gaia - stratum A', 'arcGIS - stratum B', 'gaia - stratum B']


print('\n \nSummary statistics:')
results = []
for file in PLOTFILES:
    result = get_scores_from_csv(file)
    if result is not None:
        results.append(result)
dfSummary = pd.DataFrame(results)
dfSummary['filename'] = plotLabels
print(dfSummary)
print(dfSummary.columns, dfSummary.shape)


#box_data = dfSummary['scores'].dropna().to_list()
#print(box_data)

arcGISstratumA = dfSummary['scores'][0]
cleanedAA = arcGISstratumA[~np.isnan(arcGISstratumA)]
GAIAstratumA = dfSummary['scores'][1]
cleanedGA = GAIAstratumA[~np.isnan(GAIAstratumA)]
arcGISstratumB = dfSummary['scores'][2]
cleanedAB = arcGISstratumB[~np.isnan(arcGISstratumB)]
GAIAstratumB = dfSummary['scores'][3]
cleanedGB = GAIAstratumB[~np.isnan(GAIAstratumB)]
summary_data = [cleanedAA, cleanedGA, cleanedAB, cleanedGB]

def set_axis_style(ax, labels):
    
    ax.set_xlim(0.25, len(labels) + 0.75)
    ax.set_xlabel('Sample name')

fig, ax = plt.subplots(1,1)
ax.violinplot(summary_data, vert=False)
ax.set_yticks(np.arange(1, 5), labels=dfSummary['filename'])
ax.set_ylim(4.5, 0.5)
ax.set_xlabel("Scores")
ax.set_title("Geocoding Scores by Stratum by Method")
#plt.violinplot(box_data, vert=False, patch_artist=True, labels=dfSummary['filename'])

plt.tight_layout()
plt.savefig('violinPlot.png')
#print(pd.DataFrame(results))






print('\n \nCity/State/Zip verifications:')
verifications = []
mismatches = []
for file in ARCFILES + DGFILES:
    verify, mismatchTable = matchCityStateZip(file)
    verifications.append(verify)
    mismatches.append(pd.DataFrame(mismatchTable))


zipTable = pd.DataFrame(verifications)
zipTable = zipTable.loc[[1, 4, 3, 5], ['zipCodeMatch', 'Nan zip codes', 'Diff zip codes']]
zipTable.index = plotLabels
zipTable.columns = ['Zip Match', 'Zip NULL', 'Different Zip']


print()
print(zipTable)







print('\n \nMismatched addresses: ', len(FLAGGED_ADDRESSES))

stratumAflags = []
stratumBflags = []
for file in ARCFILES + DGFILES:
    if file in STRATUMA:
        stratumAflags.append(getFlaggedRows(file))
    else:
        stratumBflags.append(getFlaggedRows(file))

merged_df_A = stratumAflags[0]
for df in stratumAflags[1:]:
    merged_df_A = merged_df_A.merge(df, on='address', how='outer')

merged_df_B = stratumBflags[0]
for df in stratumBflags[1:]:
    merged_df_B = merged_df_B.merge(df, on='address', how='outer')

merged_df_A.to_csv("flags_stratumA.csv", sep=",")
merged_df_B.to_csv("flags_stratumB.csv", sep=",")



