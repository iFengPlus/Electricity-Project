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
    print(f"[备份] 生成每日备份文件: {file_name}")

def main_simulation():

    meter_data = load_meter_data("meter_data.json")
    all_readings = sort_all_readings(meter_data)
    
    sim_start = datetime(2025, 2, 1, 0, 0, 0)
    sim_end   = datetime(2025, 2, 3, 1, 0, 0)  # 2月3日 1:00 结束

    read_so_far = {}

    for m_id in meter_data.keys():
        read_so_far[m_id] = []

    current_day_midnight = sim_start  # 2025-02-01 00:00
    backup_data(read_so_far, current_day_midnight)

    print("[跳过] 从 0:00 到 1:00 无数据，等待 2 秒以模拟 1 小时...")
    time.sleep(2)
    sim_clock = sim_start + timedelta(hours=1)  # 2025-02-01 1:00

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
                sleep_sec = hours_diff * 2  # 1 小时 => 2 秒
                if sleep_sec > 0:
                    print(f"[跨日] 从 {prev_dt} 睡到 {next_day_midnight} (共 {hours_diff:.2f} 小时) => sleep({sleep_sec:.2f}s)")
                    time.sleep(sleep_sec)
                    prev_dt = next_day_midnight

                backup_data(read_so_far, next_day_midnight)

                print(f"[跳过] {next_day_midnight} ~ {next_day_midnight + timedelta(hours=1)} 无数据 => 等待 2s")
                time.sleep(2)
                prev_dt = next_day_midnight + timedelta(hours=1)
                
                if prev_dt >= sim_end:
                    return

        hours_diff = (dt - prev_dt).total_seconds() / 3600.0
        if hours_diff > 0:
            sleep_sec = hours_diff * 2  
            print(f"[读数前等待] 从 {prev_dt} 到 {dt}, 差 {hours_diff*60:.1f} 分钟 => sleep({sleep_sec:.2f}s)")
            time.sleep(sleep_sec)
        
        print(f"  -> 读到[{meter_id}] 在 [{dt}] 的读数: {reading}")
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
            print(f"[跨日] 从 {prev_dt} 到 2/3 0:00 => sleep({sleep_sec:.2f}s)")
            time.sleep(sleep_sec)
        backup_data(read_so_far, final_midnight_2_3)
        print("[跳过] 2/3 0:00 ~ 1:00 无数据 => 等待 2s")
        time.sleep(2)
    
    print("\n[结束] 已到达 2025-02-03 1:00，模拟结束。")
    print(f"共读取到数据量：{sum(len(v) for v in read_so_far.values())} 条。")

if __name__ == "__main__":
    main_simulation()
