# AI-LAB Prometheus Rules Sync Validation 01

## Result
- Verdict: PASS
- `ai_lab:runtime_health_score` exists in repo, is loaded in Prometheus, and returns a value
- No rules were modified
- No services were restarted

## Git
- HEAD: `f23bc0db`
- Branch: `main`
- Status before report commit: clean
- Branch state before report commit: `main...origin/main`

## Prometheus State
- Local `127.0.0.1:9090` was not reachable from this shell
- Remote Prometheus at `192.168.1.40:9090` was `Ready` and `Healthy`
- No Prometheus restart was performed
- No Grafana restart was performed

## Repo Rules Found
- `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml`
- `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml.bak`
- `monitorizacion/prometheus/README.md`

## Rule Definition in Repo
- `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` defines:
  - recording rule `ai_lab:runtime_health_score`
  - recording group `ai_lab_cognitive_recording_rules`
- `monitorizacion/prometheus/README.md` also documents `ai_lab:runtime_health_score`

## Prometheus Loaded Rules
- `/api/v1/status/config` reports:
  - `config.file: /etc/prometheus/prometheus.yml`
  - `rule_files:`
    - `/etc/prometheus/rules/ai-lab-route-family-alerts.yml`
    - `/etc/prometheus/rules/ai-lab-cognitive-alerts.yml`
- `/api/v1/rules` shows `ai_lab_cognitive_recording_rules` loaded with:
  - `ai_lab:federation_guard_events_rate5m`
  - `ai_lab:evidence_replay_rate5m`
  - `ai_lab:slo_violations_rate5m`
  - `ai_lab:architecture_risk_score`
  - `ai_lab:runtime_health_score`

## Query Results
- `query(ai_lab:runtime_health_score)` returned `1`
- `query(ailab_cognitive_health_score)` returned `0`
- `query(up)` showed relevant targets up, including:
  - `ai-lab-gateway` `up=1`
  - `ai-lab-router` `up=1`
  - `ai-lab-live-api` `up=1`
  - `ai-lab-cadvisor` `up=1`
  - `ai-lab-node` `up=1`

## Loading Errors
- No rule-loading errors were observed in the Prometheus API responses checked
- No parse/load failure evidence was found in the validated runtime responses

## Repo vs Runtime
- Classification: A
- The rule exists in repo and is loaded in Prometheus
- The query returns a non-empty vector, so this is not a missing-rule sync issue
- The rule appears to be a separate recording signal from the NOC runtime critical path

## Dashboard / Docs Dependents
- `monitorizacion/prometheus/README.md` documents the rule
- `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` includes the rule and drift alert that references it
- No Grafana dashboard files surfaced in the searched paths for this metric

## Operational Risk
- Low
- The rule is present and healthy from Prometheus’ perspective
- The main residual semantic gap is that this recording rule does not directly mirror the NOC `no_nodes_online` critical state

## Constraints Observed
- No rule files were modified
- No Prometheus/Grafana restart was performed
- No services were touched
- No inference backend was started
- No push was performed
- No tag was created

## Recommended Next Phase
- Optional semantic review only: validate whether `ai_lab:runtime_health_score` should align more explicitly with `no_nodes_online` / runtime critical semantics
