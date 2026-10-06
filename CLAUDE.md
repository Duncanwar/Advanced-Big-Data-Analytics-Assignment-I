# CLAUDE.md

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
