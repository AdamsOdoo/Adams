# Scenario 8 topology evidence — genuine two-instance topology C (single host)
captured_at_utc: 2026-07-11T22:47:42Z

## Two independent odoo-bin application-server processes (CURRENT, after an independent restart mid-scenario)
  PID  PPID     ELAPSED CMD
 3884     1       03:21 /opt/odoo-venv/bin/python /opt/odoo/odoo-bin -c /opt/odoo.conf -d pbscen --http-port 8169 --workers=0 --max-cron-threads=0 --no-database-list --log-level=warn
  PID  PPID     ELAPSED CMD
 3885     1       03:21 /opt/odoo-venv/bin/python /opt/odoo/odoo-bin -c /opt/odoo.conf -d pbscen --http-port 8170 --workers=0 --max-cron-threads=0 --no-database-list --log-level=warn

server1: PID 3884, http-port 8169, --workers=0 --max-cron-threads=0
server2: PID 3885, http-port 8170, --workers=0 --max-cron-threads=0
shared database: pbscen on one PostgreSQL 16.14 cluster (127.0.0.1:5433)
independently restartable: YES (both were killed and relaunched independently mid-session; PIDs changed from 30739/30740 to 3884/3885)

## Concurrency mechanism: barrier-synchronized XML-RPC run_drain to BOTH servers
## drain rounds (both servers fire run_drain within ~1-2ms of each other):
{"tag": "srv1-r1", "port": "8169", "server_version": "19.0", "uid": 2, "t_before": "22:46:27.260082", "t_after": "22:46:27.266900", "drain_ok": true, "note": "run_drain returned None (normal); committed server-side"}
{"tag": "srv2-r1", "port": "8170", "server_version": "19.0", "uid": 2, "t_before": "22:46:27.258796", "t_after": "22:46:27.310719", "drain_ok": true, "note": "run_drain returned None (normal); committed server-side"}
{"tag": "srv1-r2", "port": "8169", "server_version": "19.0", "uid": 2, "t_before": "22:46:27.862491", "t_after": "22:46:27.869702", "drain_ok": true, "note": "run_drain returned None (normal); committed server-side"}
{"tag": "srv2-r2", "port": "8170", "server_version": "19.0", "uid": 2, "t_before": "22:46:27.860647", "t_after": "22:46:27.900583", "drain_ok": true, "note": "run_drain returned None (normal); committed server-side"}

## Verified: 40/40 pool jobs succeeded; 0 stuck 'running'; every job exactly 2 log rows
## (no cross-server double-processing); exactly 1 claim-attempt per job; 0 deadlocks.

## LIMITATION: single physical host, single code checkout. This is two independent
## application-SERVER PROCESSES sharing one DB (topology C by the plan's definition),
## but NOT a multi-host / multi-VM / Odoo.sh multi-node deployment. Proposed: SRR-09
## REDUCED (single-host two-instance evidence), NOT closed. ChatGPT decides whether
## true multi-node proof is still required.
