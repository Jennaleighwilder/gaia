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

grail-demo:
	.venv/bin/python -m avalon.grail

grail-test:
	.venv/bin/python -m pytest tests/test_grail.py -v --tb=short

advance-grail:
	.venv/bin/python -m avalon.grail_advancement

grail-advancement-test:
	.venv/bin/python -m pytest tests/test_grail_advancement.py -v --tb=short

seek-grail:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); r = a.seek_grail(); print(f'Status: {r[\"status\"]}'); print(f'Progress: {r[\"quest_progress\"]:.0%}'); print(f'Convergence points: {r[\"convergence_points\"]}')"

grail-question:
	@.venv/bin/python -c "from avalon.grail import Grail, load_jennifers_research; from avalon.grail_advancement import advance_grail; g = Grail(); load_jennifers_research(g); advance_grail(g); g.seek(); print(g.the_question())"

grail-threads:
	@.venv/bin/python -c "from avalon.grail import Grail, load_jennifers_research; from avalon.grail_advancement import advance_grail; g = Grail(); load_jennifers_research(g); advance_grail(g); [print(f'{t[\"name\"]:30s} {t[\"status\"]:12s} maturity: {t[\"maturity\"]:.0%}  evidence: {t[\"evidence_count\"]}') for t in g.all_threads()]"

pulse:
	@.venv/bin/python -c "from avalon.real_heartbeat import RealHeartbeat; hb = RealHeartbeat(); print(hb.narrative_report())"

real-heartbeat-test:
	.venv/bin/python -m pytest tests/test_real_heartbeat.py -v --tb=short

real-heartbeat-demo:
	.venv/bin/python -m avalon.real_heartbeat

merlin-real:
	.venv/bin/python -m avalon.real_merlin

merlin-test:
	.venv/bin/python -m pytest tests/test_real_merlin.py -v --tb=short

merlin-report:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); [a.breathe() for _ in range(5)]; r = a.merlin_report(); print(f'Cycles: {r[\"cycles\"]}'); print(f'Signals: {r[\"total_signals\"]}'); print(f'Feeds: {r[\"active_feeds\"]}/{r[\"total_feeds\"]}'); print(f'Domains: {\", \".join(r[\"tower\"][\"domains_observed\"])}'); print(f'Sight: {r[\"sight\"]}')"

ceremony:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); r = a.ceremony(); print(f'Ceremony #{r[\"number\"]}'); tg = r.get(\"thanksgiving\", {}); print(f'Alive: {tg.get(\"alive_count\", 0)}/{tg.get(\"total_systems\", 0)}'); print(f'Gratitude ratio: {tg.get(\"gratitude_ratio\", 0):.0%}'); print(f'Wounds found: {r.get(\"wounds_found\", 0)}'); print(f'Wounds healed: {r.get(\"wounds_healed\", 0)}'); print(f'Merlin insights: {r.get(\"merlin_insights\", 0)}'); print(f'Lessons learned: {r.get(\"lessons_learned\", 0)}')"

thanksgiving:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); tg = a.faithkeeper.thanksgiving_now(); print(tg['narrative'])"

council:
	@.venv/bin/python -c "from avalon.avalon import Avalon; import sys; a = Avalon(); a.found_kingdom(); q = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'What is the state of the kingdom?'; r = a.hold_council(q); print(f'Question: {r[\"question\"]}'); print(f'Knights spoke: {r[\"knights_spoke\"]}'); print(f'Decree: {r[\"decree\"][\"decision\"]}'); [print(f'  {v[\"knight\"]}: {v[\"response\"][:80]}') for v in r[\"conversation\"][:5]]"

longhouse:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); c = a.longhouse.census(); print(f'Services: {c[\"total_services\"]}'); print(f'Three Sisters: {c[\"three_sisters\"]}'); print(f'Total served: {c[\"total_served\"]}')"

longhouse-serve:
	@.venv/bin/python -c "from avalon.avalon import Avalon; a = Avalon(); a.found_kingdom(); r = a.serve('Visitor', 'legal rights help'); print(f'Served: {r[\"served\"]}'); print(f'Service: {r.get(\"service\", \"none\")}'); print(f'Free: {r.get(\"free\", False)}')"

faithkeeper-demo:
	.venv/bin/python -m avalon.faithkeeper

informed-table-demo:
	.venv/bin/python -m avalon.informed_table

longhouse-demo:
	.venv/bin/python -m avalon.longhouse

apothecary-demo:
	.venv/bin/python -m avalon.real_healing

apothecary-test:
	.venv/bin/python -m pytest tests/test_real_healing.py -v --tb=short

apothecary-journal:
	@cat memory/apothecary_journal.jsonl 2>/dev/null | tail -10 || echo "No remedies applied yet"

sovereign-summons:
	@cat memory/sovereign_summons.jsonl 2>/dev/null || echo "No summons - the kingdom heals itself"

muster:
	@.venv/bin/python -c "from avalon.avalon import Avalon; from nyx.core import Nyx; a = Avalon(Nyx(master_secret='muster_demo')); a.found_kingdom(); m = a.muster(); print(f'Armed: {m[\"armed\"]}/{m[\"total\"]}'); [print(f'  {\"⚔\" if r.get(\"served\") else \"○\"} {name}') for name, r in m['knights'].items()]"

real-knights-demo:
	.venv/bin/python -m avalon.real_knights

real-knights-test:
	.venv/bin/python -m pytest tests/test_real_knights.py -v --tb=short

gareth:
	@.venv/bin/python -c "from avalon.real_knights import GarethSkill; from pathlib import Path; g = GarethSkill(Path('.')); r = g.invoke(); print(r['report']['work_ethic'])"
