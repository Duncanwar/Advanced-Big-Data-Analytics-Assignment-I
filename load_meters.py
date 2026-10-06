import psycopg
import smart_meter_simulator

DSN = "host=localhost port=5432 dbname=tsdb user=postgres password=postgres"

meters = smart_meter_simulator.meter_metadata()
print(f"Loading {len(meters)} meters into the database...")

with psycopg.connect(DSN) as conn:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO meters (meter_id, region, customer_type, base_power_kw, power_factor)
            VALUES (%(meter_id)s, %(region)s, %(customer_type)s, %(base_power_kw)s, %(power_factor)s)
            ON CONFLICT (meter_id) DO NOTHING
            """,
            meters,
        )
        cur.execute("SELECT count(*) FROM meters")
        print("Rows in meters table:", cur.fetchone()[0])
