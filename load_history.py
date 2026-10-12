import csv
import os
import time
from datetime import datetime

import psycopg

import smart_meter_simulator

DSN = "host=localhost port=5432 dbname=tsdb user=postgres password=postgres"
CSV_PATH = "energy_readings.csv"
FIELDS = ["meter_id", "event_time", "received_time", "power_kw",
          "voltage_v", "current_a", "frequency_hz", "energy_kwh"]
BATCH_SIZE = 100_000
CAT = smart_meter_simulator.CAT


def now_cat():
    return datetime.now(CAT).strftime("%Y-%m-%d %H:%M:%S CAT")

def generate_csv():
    consumed = 0
    batch = []
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for reading in smart_meter_simulator.iter_readings():
            batch.append(reading)
            consumed += 1
            if len(batch) == BATCH_SIZE:
                writer.writerows(batch)
                batch.clear()
                if consumed % 1_000_000 == 0:
                    print(f"  generated {consumed:,} readings")
        if batch:                     # write the last, smaller batch
            writer.writerows(batch)
    return consumed

def count_csv_rows():
    with open(CSV_PATH, "rb") as f:
        return sum(1 for _ in f) - 1

def load_csv(conn):
    copy_sql = f"COPY energy_readings ({', '.join(FIELDS)}) FROM STDIN WITH (FORMAT csv, HEADER true)"
    file_size = os.path.getsize(CSV_PATH)
    sent = 0
    with conn.cursor() as cur:
        load_start = time.perf_counter()
        with open(CSV_PATH, "rb") as f, cur.copy(copy_sql) as copy:
            while block := f.read(8 * 1024 * 1024):
                copy.write(block)
                sent += len(block)
                print(f"  loaded {100 * sent / file_size:5.1f}%", end="\r")
        conn.commit()
        load_seconds = time.perf_counter() - load_start
        cur.execute("SELECT count(*) FROM energy_readings")
        db_rows = cur.fetchone()[0]
    print()
    return load_seconds, db_rows

def main():
    info = smart_meter_simulator.dataset_info()
    expected = info["expected_counts"]["emitted_readings"]
    print("Expected counts:", info["expected_counts"])
    print("Planned readings:", info["planned_readings"])

    with psycopg.connect(DSN) as conn:
        if conn.execute("SELECT count(*) FROM energy_readings").fetchone()[0] != 0:
            raise SystemExit("energy_readings is not empty - TRUNCATE it first")

        print(f"[{now_cat()}] Phase 1: generating CSV")
        total_start = time.perf_counter()
        consumed = generate_csv()
        generation_seconds = time.perf_counter() - total_start
        csv_rows = count_csv_rows()
        print(f"[{now_cat()}] Generation done: {consumed:,} dictionaries, "
              f"{csv_rows:,} CSV rows, {generation_seconds:.1f} s")

        print(f"[{now_cat()}] Phase 2: loading with COPY")
        load_seconds, db_rows = load_csv(conn)
        total_seconds = time.perf_counter() - total_start
        print(f"[{now_cat()}] Load done: {db_rows:,} rows, {load_seconds:.1f} s")

    print("\n===== Summary =====")
    print(f"Expected emitted readings:   {expected:,}")
    print(f"Dictionaries consumed:       {consumed:,}")
    print(f"CSV data rows:               {csv_rows:,}")
    print(f"energy_readings rows:        {db_rows:,}")
    print("All agree:", consumed == csv_rows == db_rows == expected)
    print(f"Generation seconds: {generation_seconds:.1f}")
    print(f"Load seconds:       {load_seconds:.1f}")
    print(f"Total seconds:      {total_seconds:.1f}")


if __name__ == "__main__":
    main()
