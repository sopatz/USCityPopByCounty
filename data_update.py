import requests 
import zipfile
import io
import pandas as pd
import re
import os
import subprocess

# =================================================================================================
#  This script checks for updates to both:
#   - US Cities data: https://simplemaps.com/data/us-cities
#   - US Counties data: https://simplemaps.com/data/us-counties
# 
#  If new data is available, it downloads the ZIP, extracts the CSV,
#  converts it to JSON, and commits the changes to GitHub.
# =================================================================================================

# ------------------- Cities Constants -------------------
CITY_DATA_PAGE_URL = "https://simplemaps.com/data/us-cities"
CITY_ZIP_BASE_URL = "https://simplemaps.com/static/data/us-cities/"
CITY_ZIP_FILE_PATTERN = r"us-cities/([\d\.]+)/basic/simplemaps_uscities_basicv([\d\.]+)\.zip"

CITY_CSV_FILE = "uscities.csv"
CITY_JSON_FILE = "city_population.json"
CITY_VERSION_FILE = "latest_version.txt"

# ------------------- Counties Constants -------------------
COUNTY_DATA_PAGE_URL = "https://simplemaps.com/data/us-counties"
COUNTY_ZIP_BASE_URL = "https://simplemaps.com/static/data/us-counties/"
COUNTY_ZIP_FILE_PATTERN = r"us-counties/([\d\.]+)/basic/simplemaps_uscounties_basicv([\d\.]+)\.zip"

COUNTY_CSV_FILE = "uscounties.csv"
COUNTY_JSON_FILE = "county_data.json"
COUNTY_VERSION_FILE = "latest_county_version.txt"

# ------------------- Shared Files -------------------
STATUS_FILE = "update_status.txt"

# ------------------- Logging -------------------
def log_update_status(message):
    """Log update status to a file with UTF-8 encoding."""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(message)

# ------------------- Version Helpers -------------------
def get_stored_version(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return f.read().strip()
    return None

def save_new_version(file, version):
    with open(file, "w") as f:
        f.write(version)

# ------------------- Web Scraping for Version -------------------
def get_latest_version(data_url, zip_base_url, pattern, kind):
    """Generic function to get latest version and ZIP URL."""
    print(f"Checking for latest {kind} version...")
    response = requests.get(data_url)
    if response.status_code == 200:
        match = re.search(pattern, response.text)
        if match:
            version = match.group(1)
            zip_url = f"{zip_base_url}{version}/basic/simplemaps_us{kind}basicv{version}.zip"
            return version, zip_url
    print(f"Failed to retrieve the latest {kind} version.")
    return None, None

# ------------------- Download and Extract -------------------
def download_and_extract_zip(zip_url, expected_file):
    print(f"Downloading data from {zip_url}...")
    response = requests.get(zip_url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extract(expected_file)
        print(f"Extracted: {expected_file}")
    else:
        print(f"Failed to download {expected_file}.")
        log_update_status(f"❌ Failed to download {expected_file}.")
        exit(1)

# ------------------- Conversion -------------------
def convert_city_csv_to_json():
    df = pd.read_csv(CITY_CSV_FILE)
    df = df[["city", "state_id", "state_name", "county_fips", "county_name", "lat", "lng", "population"]]
    df.to_json(CITY_JSON_FILE, orient="records", indent=4)
    print(f"Converted to JSON: {CITY_JSON_FILE}")

def convert_county_csv_to_json():
    df = pd.read_csv(COUNTY_CSV_FILE)
    #print(df.columns)
    df = df[["county", "county_full", "county_fips", "state_name", "lat", "lng", "population"]]
    df.to_json(COUNTY_JSON_FILE, orient="records", indent=4)
    print(f"Converted to JSON: {COUNTY_JSON_FILE}")

# ------------------- Git Commit -------------------
def commit_and_push(files, message):
    print("Committing and pushing to GitHub...")
    subprocess.run(["git", "add"] + files)
    subprocess.run(["git", "commit", "-m", message])
    subprocess.run(["git", "push", "origin", "main"])  # Update branch name if needed

# ------------------- Main Logic -------------------
if __name__ == "__main__":
    status_messages = []

    # --- Cities ---
    latest_city_version, city_zip_url = get_latest_version(
        CITY_DATA_PAGE_URL, CITY_ZIP_BASE_URL, CITY_ZIP_FILE_PATTERN, kind="cities_"
    )
    stored_city_version = get_stored_version(CITY_VERSION_FILE)

    if latest_city_version and latest_city_version != stored_city_version:
        print(f"New CITY version: {latest_city_version} (Old: {stored_city_version})")
        download_and_extract_zip(city_zip_url, CITY_CSV_FILE)
        convert_city_csv_to_json()
        save_new_version(CITY_VERSION_FILE, latest_city_version)
        commit_and_push([CITY_JSON_FILE, CITY_VERSION_FILE], "Automated update of city_population.json")
        status_messages.append(f"✅ City data updated to version {latest_city_version}")
    elif latest_city_version:
        print("City data is already up to date.")
        status_messages.append(f"❌ City data is up to date (version {stored_city_version})")
    else:
        status_messages.append("❌ Failed to check for city updates.")

    # --- Counties ---
    latest_county_version, county_zip_url = get_latest_version(
        COUNTY_DATA_PAGE_URL, COUNTY_ZIP_BASE_URL, COUNTY_ZIP_FILE_PATTERN, kind="counties_"
    )
    stored_county_version = get_stored_version(COUNTY_VERSION_FILE)

    if latest_county_version and latest_county_version != stored_county_version:
        print(f"New COUNTY version: {latest_county_version} (Old: {stored_county_version})")
        download_and_extract_zip(county_zip_url, COUNTY_CSV_FILE)
        convert_county_csv_to_json()
        save_new_version(COUNTY_VERSION_FILE, latest_county_version)
        commit_and_push([COUNTY_JSON_FILE, COUNTY_VERSION_FILE], "Automated update of county_data.json")
        status_messages.append(f"✅ County data updated to version {latest_county_version}")
    elif latest_county_version:
        print("County data is already up to date.")
        status_messages.append(f"❌ County data is up to date (version {stored_county_version})")
    else:
        status_messages.append("❌ Failed to check for county updates.")

    # Write final status log
    log_update_status("\n".join(status_messages))
