import requests 
import zipfile
import io
import pandas as pd
import re
import os
import subprocess

# =================================================================================================
#  Checks https://simplemaps.com/data/us-cities for updated data. If there is a new version of the 
#  US Cities data, it is downloaded, and all the city info in "city_population.json" are updated.
#
#  If new county data is needed, go to the following link and download the GeoJSON file:
#  https://public.opendatasoft.com/explore/dataset/georef-united-states-of-america-county/export/?flg=en-us&disjunctive.ste_code&disjunctive.ste_name&disjunctive.coty_code&disjunctive.coty_name
# =================================================================================================

# URL of the data page and zip file pattern
DATA_PAGE_URL = "https://simplemaps.com/data/us-cities"
ZIP_BASE_URL = "https://simplemaps.com/static/data/us-cities/"
ZIP_FILE_PATTERN = r"us-cities/([\d\.]+)/basic/simplemaps_uscities_basicv([\d\.]+)\.zip"

# File names
CSV_FILE = "uscities.csv"
JSON_FILE = "city_population.json"
VERSION_FILE = "latest_version.txt"
STATUS_FILE = "update_status.txt"

def log_update_status(message):
    """Log update status to a file with UTF-8 encoding (fixes Unicode errors)."""
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(message)

def get_latest_version():
    """Scrape the website to find the latest data version."""
    print("Checking for latest version...")
    response = requests.get(DATA_PAGE_URL)
    if response.status_code == 200:
        match = re.search(ZIP_FILE_PATTERN, response.text)
        if match:
            version = match.group(1)
            zip_url = f"{ZIP_BASE_URL}{version}/basic/simplemaps_uscities_basicv{version}.zip"
            return version, zip_url
    print("Failed to retrieve the latest version.")
    return None, None

def get_stored_version():
    """Read the last stored version from file."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return None

def save_new_version(version):
    """Save the latest version to a file."""
    with open(VERSION_FILE, "w") as f:
        f.write(version)

def download_and_extract_zip(zip_url):
    """Download and extract the latest data."""
    print(f"Downloading latest data from {zip_url}...")
    response = requests.get(zip_url)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extract(CSV_FILE)
        print(f"Extracted: {CSV_FILE}")
    else:
        print("Failed to download data.")
        log_update_status("❌ Failed to download city data.")
        exit(1)

def convert_csv_to_json():
    """Convert CSV to JSON."""
    df = pd.read_csv(CSV_FILE)
    df = df[["city", "state_id", "state_name", "county_fips", "county_name", "lat", "lng", "population"]]
    df.to_json(JSON_FILE, orient="records", indent=4)
    print(f"Converted to JSON: {JSON_FILE}")

def commit_and_push():
    """Commit and push updated JSON to GitHub."""
    print("Committing and pushing to GitHub...")
    subprocess.run(["git", "add", JSON_FILE, VERSION_FILE, STATUS_FILE])
    subprocess.run(["git", "commit", "-m", "Automated update of city_population.json"])
    subprocess.run(["git", "push", "origin", "main"])  # Change branch if needed

if __name__ == "__main__":
    latest_version, zip_url = get_latest_version()
    stored_version = get_stored_version()

    if not latest_version:
        log_update_status("❌ Failed to check for updates.")
        exit(1)

    if latest_version != stored_version:
        print(f"New version found: {latest_version} (Old: {stored_version})")
        download_and_extract_zip(zip_url)
        convert_csv_to_json()
        save_new_version(latest_version)
        commit_and_push()
        log_update_status(f"✅ Data was updated to version {latest_version}.")
    else:
        print(f"No new version. Current version ({stored_version}) is up to date.")
        log_update_status(f"❌ No new version. Current version ({stored_version}) is up to date.")
