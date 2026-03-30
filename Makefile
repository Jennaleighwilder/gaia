# GAIA — Governance of Atmospheric Intelligence and Alerts

.PHONY: up down test ingest status health pull-history backtest backtest-full download-events build-event-db national-backtest event-stats memory-stats populate-fixtures channel-separation autopsy

up:
	bash bin/gaia-up

down:
	@echo "[GAIA] Stopping..."
	@pkill -f "runtime.governor.governor" 2>/dev/null || true
	@echo "[GAIA] Stopped."

test:
	cd $(shell pwd) && python3 tests/test_pressure_engine.py

ingest:
	cd $(shell pwd) && python3 -m runtime.ingest.noaa_client

status:
	@curl -sf http://127.0.0.1:7780/health 2>/dev/null | python3 -m json.tool || echo "[GAIA] Not running."

health: status

pull-history:
	cd $(shell pwd) && python3 scripts/pull_historical_obs.py

backtest:
	cd $(shell pwd) && python3 scripts/run_backtest.py

backtest-full: pull-history backtest

download-events:
	cd $(shell pwd) && bash scripts/download_storm_events.sh

build-event-db:
	cd $(shell pwd) && python3 scripts/build_national_event_db.py

national-backtest: download-events build-event-db
	cd $(shell pwd) && python3 scripts/sample_backtest_events.py
	cd $(shell pwd) && python3 scripts/pull_national_history.py
	cd $(shell pwd) && python3 scripts/run_national_backtest.py

event-stats:
	cd $(shell pwd) && python3 -c "import json; d=json.load(open('data/event_stats.json')); [print(f'  {k}: {v}') for k,v in d.items() if not isinstance(v, dict)]"

memory-stats:
	cd $(shell pwd) && python3 -c "import json; from runtime.memory.event_memory import EventMemory; m=EventMemory(); print(json.dumps(m.compute_calibration(), indent=2))" || echo "No memory data yet."

populate-fixtures:
	cd $(shell pwd) && python3 scripts/populate_gps_pw_fixture.py
	cd $(shell pwd) && python3 scripts/populate_surface_ozone_fixture.py
	cd $(shell pwd) && python3 scripts/populate_tri_fixture.py

populate-tri:
	cd $(shell pwd) && python3 scripts/populate_tri_fixture.py

channel-separation:
	cd $(shell pwd) && python3 scripts/channel_separation_diagnostic.py

download-storm-events-tn:
	cd $(shell pwd) && bash scripts/download_noaa_storm_events_tn.sh

filter-east-tn-events:
	cd $(shell pwd) && python3 scripts/filter_east_tn_storm_events.py

autopsy: populate-fixtures
	cd $(shell pwd) && python3 scripts/false_alarm_autopsy.py

# NYX targets
heartbeat:
	.venv/bin/python scripts/nyx_heartbeat.py

nyx-test:
	.venv/bin/python -m pytest tests/test_nyx.py -v --tb=short

adapter-test:
	.venv/bin/python -m pytest tests/test_adapters.py -v --tb=short

nyx-demo:
	.venv/bin/python -m nyx.core

nyx-all:
	.venv/bin/python -m pytest tests/test_nyx.py tests/test_adapters.py tests/test_nyx_integration.py -v --tb=short

freeze-check:
	@.venv/bin/python -c "from adapters.lancelot import LancelotAdapter; la = LancelotAdapter(); print(la.verify_freeze() if la.is_available else {'frozen': False, 'reason': 'West-OS not found in frozen/'})"

merlin-sight:
	.venv/bin/python -m avalon.merlin_feeds

village-status:
	.venv/bin/python -m avalon.village_routes

fusion-demo:
	.venv/bin/python -m avalon.fusion

fusion-test:
	.venv/bin/python -m pytest tests/test_fusion.py -v --tb=short

vital-signs:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); [a.breathe() for _ in range(5)]; v = a.fusion.vital_signs(); print(f'Mood: {v[\"heartbeat\"][\"current_mood\"]}'); print(f'Joy: {v[\"joy\"][\"joy_index\"]}'); print(f'Cohesion: {v[\"love\"][\"cohesion\"]}'); print(f'Lessons: {v[\"carbon\"][\"total_lessons\"]}')"

memory-save:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); print(a.sleep())"

memory-wake:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); print('Memory:', a.memory.status)"

memory-journal:
	@.venv/bin/python -c "from avalon.memory import Memory; m = Memory(); [print(e) for e in m.read_journal(last_n=10)]"

memory-identity:
	@.venv/bin/python -c "from avalon.memory import Memory; m = Memory(); print(m.identity_across_time())"

memory-test:
	.venv/bin/python -m pytest tests/test_memory.py -v --tb=short

memory-dream:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); print(a.memory.dream(a.fusion))"

healing-demo:
	.venv/bin/python -m avalon.healing

healing-test:
	.venv/bin/python -m pytest tests/test_healing.py -v --tb=short

triage:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); print(a.healing.triage_report())"
