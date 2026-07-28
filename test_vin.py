import requests

response = requests.get('https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/1G1Y12D72H5112809?format=json&modelyear=2017')

def extract_unique_car_profile(api_response):

# Takes a raw NHTSA API response dictionary, navigates to the vehicle data, and adaptively extracts the core unique features.

   
    primary_categories = {
        "VIN": "Vehicle Identification Number",
        "Make": "Manufacturer",
        "Model": "Vehicle Model",
        "ModelYear": "Model Year",
        "Trim": "Trim",
        "BodyClass": "Body Type",
        "EngineCylinders": "Engine Cylinders",
        "DisplacementL": "Engine Size (Liters)",
        "DriveType": "Drivetrain",
        "TransmissionStyle": "Transmission Type",
        "PlantCity": "Assembly City",
        "PlantCountry": "Assembly Country"
    }
    
    
    results_list = api_response.get('Results', [])
    
    if not results_list:
        print("Error: No vehicle data found in this response.")
        return
        
    vehicle_data = results_list[0]
    
    print(f"=== Car Profile ===")
    
    # 3. Adaptively loop through our primary blueprint
    for key, human_readable_label in primary_categories.items():
        # Safely get the value. If the key doesn't even exist, default to None.
        value = vehicle_data.get(key, None)
        
        # Handle the data based on whether it's filled, blank, or missing
        if value is None:
            # The key was completely missing from the data
            print(f"{human_readable_label} ({key}): [Not Provided in Data]")
            
        elif str(value).strip() == "":
            # The key exists, but it is blank (e.g., "")
            print(f"{human_readable_label} ({key}): [Blank]")
            
        else:
            # The data is present and valid
            print(f"{human_readable_label}: {value}")
            
    print("=" * 50 + "\n")


extract_unique_car_profile(response.json())

