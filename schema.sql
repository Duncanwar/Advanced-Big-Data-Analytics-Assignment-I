CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE table If not exists energy_live (
    meter_id  BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    received_time TIMESTAMPTZ NOT NULL,
    power_kw      DOUBLE PRECISION,
    voltage_v     DOUBLE PRECISION,
    current_a     DOUBLE PRECISION,
    frequency_hz  DOUBLE PRECISION,
    energy_kwh    DOUBLE PRECISION
);

create table if not exists energy_readings (
    meter_id  BIGINT NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    received_time TIMESTAMPTZ NOT NULL,
    power_kw      DOUBLE PRECISION,
    voltage_v     DOUBLE PRECISION,
    current_a     DOUBLE PRECISION,
    frequency_hz  DOUBLE PRECISION,
    energy_kwh    DOUBLE PRECISION
);

select create_hypertable('energy_readings', by_range('event_time', interval '1 day'), if_not_exists => true);

CREATE TABLE IF NOT EXISTS meters (
    meter_id      BIGINT PRIMARY KEY,
    region        TEXT,
    customer_type TEXT,
    base_power_kw DOUBLE PRECISION,
    power_factor  DOUBLE PRECISION
);
