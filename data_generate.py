import json
from datetime import datetime, timedelta
import random

def generate_meter_data():
    meter_ids = {
        "999-999-999": 10.5,  
        "888-888-888": 8.2    
    }
    
    start_date = datetime(2025, 2, 1)
    end_date = datetime(2025, 2, 3)  
    meter_data = {meter_id: [] for meter_id in meter_ids}
    
    for meter_id, initial_reading in meter_ids.items():
        current_reading = initial_reading
        for day in range((end_date - start_date).days):
            date = start_date + timedelta(days=day)
            current_time = datetime(date.year, date.month, date.day, 1, 0) 
            
            if meter_id == "999-999-999":
                current_time += timedelta(minutes=10)  
            
            while current_time.date() == date.date():
                meter_data[meter_id].append({
                    "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "reading_kwh": round(current_reading, 1)
                })
                current_reading += random.uniform(0.5, 1.0)
                current_time += timedelta(minutes=30)
                
    return meter_data

json_data = generate_meter_data()
with open("meter_data.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, indent=2, ensure_ascii=False)

print("Data have been saved to meter_data.json")