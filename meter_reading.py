import json
import time
import os
from datetime import datetime, timedelta

def load_meter_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        meter_data = json.load(f)
    return meter_data

def sort_all_readings(meter_data):
    all_readings = []
    for meter_id, readings in meter_data.items():
        for r in readings:
            dt = datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%S")
            reading = r["reading_kwh"]
            all_readings.append((dt, meter_id, reading))
    
    all_readings.sort(key=lambda x: x[0])
    return all_readings

def backup_data(read_so_far, backup_dt):
    file_name = f"backup_{backup_dt.strftime('%Y-%m-%d')}.json"
    with open(file_name, 'w', encoding='utf-8') as f:
        json.dump(read_so_far, f, indent=2, ensure_ascii=False)
    print(f"[Backup] Generated daily backup file: {file_name}")

def main_simulation():
    meter_data = load_meter_data("meter_data.json")
    all_readings = sort_all_readings(meter_data)
    
    sim_start = datetime(2025, 2, 1, 0, 0, 0)
    sim_end   = datetime(2025, 2, 3, 1, 0, 0)

    read_so_far = {}
    
    for m_id in meter_data.keys():
        read_so_far[m_id] = []

    current_day_midnight = sim_start
    backup_data(read_so_far, current_day_midnight)

    print("[Skipping] No data from 00:00 to 01:00, waiting 2 seconds to simulate 1 hour...")
    time.sleep(2)
    sim_clock = sim_start + timedelta(hours=1)

    prev_dt = sim_clock  
    
    for (dt, meter_id, reading) in all_readings:
        if dt >= sim_end:
            break
        
        if dt < sim_clock:
            continue

        while True:
            next_day_midnight = datetime(prev_dt.year, prev_dt.month, prev_dt.day) + timedelta(days=1)
            if next_day_midnight > dt:
                break
            else:
                hours_diff = (next_day_midnight - prev_dt).total_seconds() / 3600.0
                sleep_sec = hours_diff * 2
                if sleep_sec > 0:
                    print(f"[Crossing Day] Sleeping from {prev_dt} to {next_day_midnight} ({hours_diff:.2f} hours) => sleep({sleep_sec:.2f}s)")
                    time.sleep(sleep_sec)
                    prev_dt = next_day_midnight
                
                backup_data(read_so_far, next_day_midnight)
                print(f"[Skipping] {next_day_midnight} ~ {next_day_midnight + timedelta(hours=1)} No data => Waiting 2s")
                time.sleep(2)
                prev_dt = next_day_midnight + timedelta(hours=1)
                
                if prev_dt >= sim_end:
                    return

        hours_diff = (dt - prev_dt).total_seconds() / 3600.0
        if hours_diff > 0:
            sleep_sec = hours_diff * 2  
            print(f"[Waiting before reading] From {prev_dt} to {dt}, difference {hours_diff*60:.1f} minutes => sleep({sleep_sec:.2f}s)")
            time.sleep(sleep_sec)
        
        print(f"  -> Read [{meter_id}] at [{dt}]: {reading}")
        read_so_far[meter_id].append({
            "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "reading_kwh": reading
        })
        
        prev_dt = dt
    
    final_midnight_2_3 = datetime(2025, 2, 3, 0, 0, 0)
    if prev_dt < final_midnight_2_3 < sim_end:
        hours_diff = (final_midnight_2_3 - prev_dt).total_seconds() / 3600.0
        sleep_sec = hours_diff * 2
        if sleep_sec > 0:
            print(f"[Crossing Day] From {prev_dt} to 2/3 00:00 => sleep({sleep_sec:.2f}s)")
            time.sleep(sleep_sec)
        backup_data(read_so_far, final_midnight_2_3)
        print("[Skipping] 2/3 00:00 ~ 01:00 No data => Waiting 2s")
        time.sleep(2)
    
    print("\n[End] Reached 2025-02-03 01:00, simulation completed.")
    print(f"Total readings recorded: {sum(len(v) for v in read_so_far.values())}")

if __name__ == "__main__":
    main_simulation()