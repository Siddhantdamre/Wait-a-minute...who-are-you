import pandas as pd
import pycountry
import os

# 1. Setup Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

wvs_path = os.path.join(DATA_DIR, "WVS_Cross-National_Wave_7_csv_v6_0.csv")
hofstede_path = os.path.join(DATA_DIR, "hofstede_scores.csv")
output_path = os.path.join(DATA_DIR, "world_cultural_profiles.csv")

def get_country_name(code):
    """Safely translates 'JPN' to 'Japan'"""
    try:
        # We look up the code
        country = pycountry.countries.get(alpha_3=str(code).upper())
        # FIX: Check if country is NOT None before accessing .name
        if country is not None:
            return country.name
        return None
    except Exception:
        return None

# 2. Load WVS
print("Step 1: Loading WVS data...")
# low_memory=False prevents the DtypeWarning
wvs_raw = pd.read_csv(wvs_path, low_memory=False)

# 3. Extract and Process WVS
print("Step 2: Processing WVS beliefs...")
important_columns = {
    'B_COUNTRY_ALPHA': 'Country_Code',
    'Q1': 'Family_Importance',
    'Q57': 'Trust_In_People',
    'Q173': 'Religious_Importance'
}

# Only keep rows where we have a country code
wvs_shrunk = wvs_raw[list(important_columns.keys())].rename(columns=important_columns)
wvs_shrunk = wvs_shrunk.dropna(subset=['Country_Code'])

# Calculate averages per country code
wvs_country_means = wvs_shrunk.groupby('Country_Code').mean().reset_index()

# THE BRIDGE: Convert 'JPN' to 'Japan' safely
print("Step 3: Translating Country Codes to Names...")
wvs_country_means['Country'] = wvs_country_means['Country_Code'].apply(get_country_name)

# 4. Load and Standardize Hofstede
print("Step 4: Loading Hofstede scores...")
if not os.path.exists(hofstede_path):
    print(f"ERROR: {hofstede_path} not found!")
    exit()

hofstede = pd.read_csv(hofstede_path)

# Ensure Hofstede has a 'Country' column (fixes KeyError)
# We look for anything named 'country', 'Country name', etc.
for col in hofstede.columns:
    if col.lower() in ['country', 'country name', 'countries']:
        hofstede.rename(columns={col: 'Country'}, inplace=True)
        break

if 'Country' not in hofstede.columns:
    print("CRITICAL: Your Hofstede CSV is missing a 'Country' column.")
    exit()

# 5. Merge
print("Step 5: Merging datasets...")
# We use how='inner' to keep only countries found in BOTH files
master_data = pd.merge(wvs_country_means, hofstede, on='Country', how='inner')

# 6. Save
if master_data.empty:
    print("Warning: Merged data is empty! This means Country names didn't match.")
    print("Check WVS names:", wvs_country_means['Country'].head().tolist())
    print("Check Hofstede names:", hofstede['Country'].head().tolist())
else:
    master_data.to_csv(output_path, index=False)
    print(f"Success! Created {output_path} with {len(master_data)} countries.")