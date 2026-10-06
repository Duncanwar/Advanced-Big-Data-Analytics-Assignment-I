import itertools
import json
import logging

import paho.mqtt.client as mqtt

import smart_meter_simulator

BROKER_HOST = "localhost"
PORT = 1883
PILOT_SIZE = 2000

logging.basicConfig(filename="publisher.log", level=logging.INFO, format="%(asctime)s  %(levelname)s - %(message)s")

acked = 0

def on_publish(client,userdata,mid,reason_code, properties):
    global acked
    acked += 1
    logging.info("PUBACK mide=%s", mid)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="pilot-publisher")
client.on_publish = on_publish
client.connect(BROKER_HOST, PORT)
client.loop_start()

taken = 0
pending = []
for reading in itertools.islice(smart_meter_simulator.iter_readings(), PILOT_SIZE):
    taken += 1
    topic = f"energy/meters/{reading['meter_id']}"
    info = client.publish(topic, json.dumps(reading), qos=1, retain=False)
    pending.append(info)
    logging.info("SENT mid=%s topic=%s event_time=%s", info.mid, topic, reading["event_time"])

for info in pending:
    info.wait_for_publish(timeout=10)

client.loop_stop()
client.disconnect()

print(f"Dictionaries taken from generator: {taken}")
print(f"Messages acknowledged by broker: {acked}")
