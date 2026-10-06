import json
import logging

import paho.mqtt.client as mqtt
import psycopg

DSN = "host=localhost port=5432 dbname=tsdb user=postgres password=postgres"

logging.basicConfig(filename="subscriber.log", level=logging.INFO,
                    format="%(asctime)s %(message)s")

INSERT_SQL = """
    INSERT INTO energy_live (meter_id, event_time, received_time, power_kw,
                             voltage_v, current_a, frequency_hz, energy_kwh)
    VALUES (%(meter_id)s, %(event_time)s, %(received_time)s, %(power_kw)s,
            %(voltage_v)s, %(current_a)s, %(frequency_hz)s, %(energy_kwh)s)
"""

conn = psycopg.connect(DSN, autocommit=True)
received = inserted = parse_errors = insert_errors = redelivered = 0

def on_connect(client, userdata, flags, reason_code, properties):
    print("Connected, subscribing to energy/meters/#")
    client.subscribe("energy/meters/#", qos=1)

def on_message(client, userdata, msg):
    global received, inserted, parse_errors, insert_errors, redelivered
    received += 1
    if msg.dup:
        redelivered += 1
        logging.warning("REDELIVERED mid=%s topic=%s", msg.mid, msg.topic)

    try:
        reading = json.loads(msg.payload)
    except json.JSONDecodeError as exc:
        parse_errors += 1
        logging.error("PARSE ERROR topic=%s error=%s", msg.topic, exc)
        return

    try:
        conn.execute(INSERT_SQL, reading)
        inserted += 1
    except psycopg.Error as exc:
        insert_errors += 1
        logging.error("INSERT FAILED topic=%s error=%s", msg.topic, exc)

    if received % 200 == 0:
        print(f"Received {received} messages")

client = mqtct.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pilot-subscriber")
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)

try:
    client.loop_forever()
except KeyboardInterrupt:
    pass
finally:
    client.disconnect()
    conn.close()
    print(f"Messages received by subscriber: {received}")
    print(f"Rows inserted: {inserted}")
    print(f"Redelivered: {redelivered}  Parse errors: {parse_errors}  Insert errors: {insert_errors}")
