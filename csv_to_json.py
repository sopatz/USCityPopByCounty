import pandas as pd

# Load CSV file (Replace 'your_file.csv' with the actual file)
df = pd.read_csv("uscities.csv")

# Convert to JSON (ensure relevant columns exist)
df.to_json("city_population.json", orient="records", indent=4)

print("JSON file created: city_population.json")