INGEST_HOST    ?= http://localhost:8000
ANALYSIS_HOST  ?= http://localhost:8001
RESULTS_DIR    := results
USERS          ?= 100
SPAWN_RATE     ?= 10
RUN_TIME       ?= 60s

.PHONY: setup run-ingest run-analyze check-slos clean

setup:
	pip install -r requirements.txt

$(RESULTS_DIR):
	mkdir -p $(RESULTS_DIR)

# Teste de carga: ingestão de logs (S4-03 — SLO: P95 < 100ms @ 100 RPS)
run-ingest: $(RESULTS_DIR)
	locust -f locustfile.py \
		--host $(INGEST_HOST) \
		--users $(USERS) \
		--spawn-rate $(SPAWN_RATE) \
		--run-time $(RUN_TIME) \
		--headless \
		--csv $(RESULTS_DIR)/ingest \
		--only-summary \
		--loglevel WARNING

# Teste de carga: análise pelo IRA (1 usuário — respeita rate limit de 10/min)
run-analyze: $(RESULTS_DIR)
	ANALYSIS_HOST=$(ANALYSIS_HOST) \
	locust -f locustfile.py \
		--host $(ANALYSIS_HOST) \
		--users 1 \
		--spawn-rate 1 \
		--run-time $(RUN_TIME) \
		--headless \
		--csv $(RESULTS_DIR)/analyze \
		--only-summary \
		--loglevel WARNING

# Valida SLOs contra o último relatório de ingestão
check-slos: $(RESULTS_DIR)/ingest_stats.csv
	python check_slos.py $(RESULTS_DIR)/ingest_stats.csv

clean:
	rm -rf $(RESULTS_DIR)
