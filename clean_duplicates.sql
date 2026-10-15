BEGIN;

CREATE TEMP TABLE dup_pairs ON COMMIT DROP AS
SELECT meter_id, event_time
FROM energy_readings
GROUP BY meter_id, event_time
HAVING count(*) > 1
   AND count(DISTINCT (received_time, power_kw, voltage_v, current_a,
                       frequency_hz, energy_kwh)) = 1;

CREATE TEMP TABLE kept_rows ON COMMIT DROP AS
SELECT DISTINCT r.*
FROM energy_readings r
JOIN dup_pairs d USING (meter_id, event_time);

DELETE FROM energy_readings r
USING dup_pairs d
WHERE r.meter_id = d.meter_id AND r.event_time = d.event_time;

INSERT INTO energy_readings SELECT * FROM kept_rows;

COMMIT;

VACUUM ANALYZE energy_readings;
