import requests
import zipfile
import io
import pandas as pd
import re
import os
import subprocess

# =================================================================================================
#  This script checks for updates to:
#  1. US Cities data from https://simplemaps.com/data/us-cities
#  2. US Counties data from https://public.opendatasoft.com
# =================================================================================================

# ---------- City Data (SimpleMaps) ----------
CITY_DATA_PAGE_URL = "https://simplemaps.com/data/us-cities"
CITY_ZIP_BASE_URL = "https://simplemaps.com/static/data/us-cities/"
CITY_ZIP_FILE_PATTERN = r"us-cities/([\d\.]+)/basic/simplemaps_uscities_basicv([\d\.]+)\.zip"

CITY_CSV_FILE = "uscities.csv"
CITY_JSON_FILE = "city_population.json"
CITY_VERSION_FILE = "latest_city_version.txt"

# ---------- County Data (OpenDataSoft) ----------
COUNTY_GEOJSON_URL = "https://public.opendatasoft.com/api/explore/v2.1/catalog/datasets/georef-united-states-of-america-county/exports/geojson?lang=en&timezone=America%2FNew_York"
COUNTY_GEOJSON_FILE = "counties.geojson"
COUNTY_VERSION_FILE = "latest_county_version.txt"


# =============== CITY DATA FUNCTIONS ===============
def get_latest_city_version():
    """Scrape SimpleMaps to find the latest city data version."""
    print("Checking for latest city data version...")
    response = requests.get(CITY_DATA_PAGE_URL)
    if response.status_code == 200:
        match = re.search(CITY_ZIP_FILE_PATTERN, response.text)
        if match:
            version = match.group(1)
            zip_url = f"{CITY_ZIP_BASE_URL}{version}/basic/simplemaps_uscities_basicv{version}.zip"
            return version, zip_url
    print("Failed to retrieve the latest city data version.")
    return None, None

def get_stored_version(version_file):
    """Read the last stored version from file."""
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            return f.read().strip()
    return None

def save_new_version(version_file, version):
    """Save the latest version to a file."""
    with open(version_file, "w") as f:
        f.write(version)

def download_and_extract_zip(zip_url):
    """Download and extract the latest city data."""
    print(f"Downloading latest city data from {zip_url}...")
    response = requests.get(zip_url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extract(CITY_CSV_FILE)
        print(f"Extracted: {CITY_CSV_FILE}")
    else:
        print("Failed to download city data.")
        exit(1)

def convert_csv_to_json():
    """Convert city CSV to JSON."""
    df = pd.read_csv(CITY_CSV_FILE)
    df = df[["city", "state_id", "state_name", "county_fips", "county_name", "lat", "lng", "population"]]
    df.to_json(CITY_JSON_FILE, orient="records", indent=4)
    print(f"Converted to JSON: {CITY_JSON_FILE}")


# =============== COUNTY DATA FUNCTIONS ===============
def get_latest_county_version():
    """Check OpenDataSoft metadata for the latest modification date."""
    print("Checking for latest county data version...")
    response = requests.head(COUNTY_GEOJSON_URL)  # Use HEAD to get metadata
    if response.status_code == 200:
        last_modified = response.headers.get("Last-Modified", "").strip()
        return last_modified
    print("Failed to retrieve county data metadata.")
    return None

def download_county_geojson():
    """Download the latest counties.geojson file."""
    print(f"Downloading latest county data from {COUNTY_GEOJSON_URL}...")
    response = requests.get(COUNTY_GEOJSON_URL)
    if response.status_code == 200:
        with open(COUNTY_GEOJSON_FILE, "wb") as f:
            f.write(response.content)
        print(f"Saved new county data: {COUNTY_GEOJSON_FILE}")
    else:
        print("Failed to download county data.")
        exit(1)


# =============== GIT UPDATE FUNCTION ===============
def commit_and_push():
    """Commit and push updated data to GitHub."""
    print("Committing and pushing to GitHub...")
    subprocess.run(["git", "add", CITY_JSON_FILE, CITY_VERSION_FILE, COUNTY_GEOJSON_FILE, COUNTY_VERSION_FILE])
    subprocess.run(["git", "commit", "-m", "Automated update of city and county data"])
    subprocess.run(["git", "push", "origin", "main"])  # Change branch if needed


# =============== MAIN EXECUTION ===============
if __name__ == "__main__":
    # 1️⃣ CHECK & UPDATE CITY DATA
    latest_city_version, city_zip_url = get_latest_city_version()
    stored_city_version = get_stored_version(CITY_VERSION_FILE)

    if latest_city_version and latest_city_version != stored_city_version:
        print(f"New city data version found: {latest_city_version} (Old: {stored_city_version})")
        download_and_extract_zip(city_zip_url)
        convert_csv_to_json()
        save_new_version(CITY_VERSION_FILE, latest_city_version)
    else:
        print(f"No new city data version. Current version ({stored_city_version}) is up to date.")

    # 2️⃣ CHECK & UPDATE COUNTY DATA
    latest_county_version = get_latest_county_version()
    stored_county_version = get_stored_version(COUNTY_VERSION_FILE)

    if latest_county_version and latest_county_version != stored_county_version:
        print(f"New county data version found: {latest_county_version} (Old: {stored_county_version})")
        download_county_geojson()
        save_new_version(COUNTY_VERSION_FILE, latest_county_version)
    else:
        print(f"No new county data version. Current version ({stored_county_version}) is up to date.")

    # 3️⃣ PUSH CHANGES TO GITHUB (IF ANY UPDATES)
    commit_and_push()