# CLAUDE.md

AUCA Advanced Big Data Analytics, Assignment I: ingest, clean and analyse readings from
4,000 simulated smart meters (MQTT → TimescaleDB). All times are CAT (Africa/Kigali, UTC+2).

## Working agreement

- The student writes all processing and database code. Claude explains, gives snippets in chat
  and checks results (read-only queries), but does **not** create or edit project code files.
- `smart_meter_simulator.py` is supplied and must stay **unchanged**.
- Every required screenshot is full screen: command, result, Dock and menu-bar clock visible.

## Setup

- `docker compose up -d` starts `tsdb` (timescale/timescaledb:latest-pg16) and `emqx` (MQTT on 1883,
  dashboard on <http://localhost:18083>, `admin` / `public`).
- Python scripts run locally in `.venv` (`psycopg[binary]`, `paho-mqtt` 2.1.0, which needs
  `CallbackAPIVersion.VERSION2`).
- Database: `host=localhost port=5432 dbname=tsdb user=postgres password=postgres`.
  The database time zone is set with `ALTER DATABASE tsdb SET timezone = 'Africa/Kigali'`.
- psql: `docker exec -it tsdb psql -U postgres -d tsdb` (SQL ends with `;`, backslash commands don't).

## Files

| File | Purpose |
|---|---|
| `schema.sql` | `energy_live` (regular table), `energy_readings` (hypertable, 1-day chunks on `event_time`), `meters`. Run: `docker exec -i tsdb psql -U postgres -d tsdb < schema.sql` |
| `load_meters.py` | Loads `meter_metadata()` into `meters` (4,000 rows) |
| `publisher.py` | 1.3 pilot: first 2,000 readings → `energy/meters/{meter_id}`, QoS 1, no retain; counts PUBACKs; logs to `publisher.log` |
| `subscriber.py` | 1.3 pilot: subscribes `energy/meters/#` QoS 1, inserts into `energy_live`; logs to `subscriber.log` |
| `load_history.py` | 2.1 (planned): full stream → `energy_readings.csv` in 100k batches → `COPY` into `energy_readings` |

## Progress

- [x] 1.1 Environment (see the recorded values below)
- [x] 1.2 Tables, `meters` = 4,000 rows (2,584 residential, 1,010 commercial, 406 industrial), data dictionary written
- [x] 1.3 Pilot stream: `energy_live` = 2,000 rows (keep it there)
- [x] 2.1 Full load (CSV + `COPY`, `load_history.py`): `energy_readings` = 10,696,848 rows, 4,000 meters,
      event_time 2026-09-01 00:00 to 2026-09-28 23:45 CAT, 958 MB data + 85 MB indexes = 1,043 MB, 29 chunks
      (chunks are aligned to UTC midnight, so CAT 00:00–02:00 on 1 Sep falls in an extra 31 Aug chunk).
- [x] 2.2 Data quality, all match the reference: unique 10,643,735, extra copies 53,113, delayed 213,090,
      missing 108,265. Use `grid EXCEPT SELECT meter_id, event_time FROM energy_readings` for missing pairs
      (about 1 min); a `NOT EXISTS` version ran for over 20 min. Top missing: 1000003622 (47), 1000000106 (45),
      1000000366 (45), 1000001259 (44), then a three-way tie at 43 (1000000189, 1000000295, 1000000296).

## Expected counts (`dataset_info()`)

| Count | Value |
|---|---|
| planned_readings | 10,752,000 (4,000 meters × 28 days × 96 slots) |
| emitted_readings | 10,696,848 |
| unique_readings | 10,643,735 |
| duplicate_readings (extra copies) | 53,113 |
| delayed_unique_readings | 213,090 |
| missing_readings | 108,265 |

Normal arrival = `event_time` + 15 min. Delayed arrivals = 30–180 min after `event_time`.

## Recording the test environment

Run with both containers (`tsdb`, `emqx`) up. Prints CPU, RAM, OS, storage, Python, EMQX,
PostgreSQL and TimescaleDB versions, the key PostgreSQL settings, and container/VM limits.

```bash
echo "== CPU / RAM / OS / Storage =="
sysctl -n machdep.cpu.brand_string
echo "Cores: $(sysctl -n hw.physicalcpu) (P: $(sysctl -n hw.perflevel0.physicalcpu), E: $(sysctl -n hw.perflevel1.physicalcpu))"
echo "RAM: $(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 )) GB"
sw_vers
system_profiler SPStorageDataType | grep -E "Device Name|Medium Type|Protocol" | head -3

echo "== Python =="
python3 --version

echo "== EMQX =="
docker exec emqx emqx ctl status

echo "== PostgreSQL / TimescaleDB versions and settings =="
docker exec tsdb psql -U postgres -d tsdb -c "select version();" \
  -c "select extname, extversion from pg_extension where extname='timescaledb';" \
  -c "show shared_buffers;" -c "show work_mem;" \
  -c "show max_parallel_workers_per_gather;" -c "show jit;"

echo "== Container limits =="
docker inspect tsdb emqx --format '{{.Name}}  CPUs={{.HostConfig.NanoCpus}} (1e9 = 1 CPU, 0 = no limit)  Mem={{.HostConfig.Memory}} bytes  shm={{.HostConfig.ShmSize}} bytes'

echo "== Docker Desktop VM =="
docker info --format 'Docker {{.ServerVersion}} | {{.OperatingSystem}} | VM CPUs={{.NCPU}} | VM Mem={{.MemTotal}} bytes | Kernel={{.KernelVersion}}'
```

Converting the raw output:
- **CPU limit:** `NanoCpus` / 1e9 = number of CPUs (`0` means no limit).
- **Memory:** bytes / 1024³ = GiB.
- **Kernel:** a version ending in `linuxkit` means PostgreSQL runs in a container inside Docker Desktop's Linux VM.

To keep the output as evidence, append `> environment.txt 2>&1`.

### Recorded environment (2026-10-06)

| Item | Value |
|---|---|
| CPU | Apple M2, 8 cores (4 performance + 4 efficiency) |
| RAM | 8 GB |
| OS | macOS Sonoma 14.6.1 (23G93) |
| Storage | 512 GB Apple internal NVMe SSD (AP0512Z) |
| Python | 3.13.2 |
| EMQX | 6.3.1 |
| PostgreSQL | 16.15 (aarch64, Alpine) |
| TimescaleDB | 2.30.2 |
| shared_buffers | 512MB |
| work_mem | 16MB |
| max_parallel_workers_per_gather | 2 |
| jit | off |

PostgreSQL runs in a Docker container (`tsdb`) inside Docker Desktop's LinuxKit VM
(8 vCPUs, ~3.8 GiB RAM). The `tsdb` container is limited to 4 CPUs, 2 GiB RAM and 512 MB shm.
The `emqx` container is limited to 1 GiB RAM, with no CPU limit.
