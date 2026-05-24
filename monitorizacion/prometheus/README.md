# AI-LAB Prometheus Alerting

## Alert Rules

### Deployment

Copy `rules/ai-lab-cognitive-alerts.yml` to the Prometheus host (`192.168.1.40`):

```bash
scp rules/ai-lab-cognitive-alerts.yml albert@192.168.1.40:/home/albert/docker/monitorizacion/prometheus/config/rules/
```

Then reload Prometheus:

```bash
curl -X POST http://192.168.1.40:9090/-/reload
```

### Verify

```bash
curl -s http://192.168.1.40:9090/api/v1/rules | jq '.data.groups[].rules[] | {name: .name, state: .state, type: .type}'
```

### Alert Rules (18 total)

| Category | Alert | Severity | Trigger |
|----------|-------|----------|---------|
| Federation Guards | AI-LABFederationSafeMode | critical | guard_state >= 3 |
| Federation Guards | AI-LABFederationConstrained | warning | guard_state >= 2 |
| Federation Guards | AI-LABReplayStorm | critical | rate > 25/5m |
| Federation Guards | AI-LABStormHeuristicTriggered | critical | rate > 10/5m |
| Federation Guards | AI-LABAuthorityEscalationDetected | warning | rate > 5/10m |
| Evidence Lineage | AI-LABInvalidLineage | critical | invalid > 0 |
| Evidence Lineage | AI-LABHighReplayRisk | warning | replay_risk > 10 |
| Evidence Lineage | AI-LABStaleEvidence | warning | stale > 20 |
| Evidence Lineage | AI-LABDeepLineage | warning | depth > 8 |
| Cognitive SLO | AI-LABSLOViolation | warning | violations > 0/10m |
| Cognitive SLO | AI-LABSLOSafeMode | critical | safe_mode > 0/10m |
| Cognitive SLO | AI-LABSLORegistryInconsistent | critical | consistency < 1 |
| Cognitive SLO | AI-LABGatewayUnavailable | critical | gateway < 1 |
| Cognitive SLO | AI-LABLMStudioUnavailable | critical | lmstudio < 1 |
| Model Registry | AI-LABDeprecatedAliasReappeared | warning | deprecated > 1 |
| Model Registry | AI-LABNoRoutableModels | critical | routable < 1 |
| Architecture | AI-LABGovernanceViolations | warning | violations > 10 |
| Architecture | AI-LABHighRiskArchitecture | warning | high_risk > 5 |

### Recording Rules (5 total)

| Rule | Description |
|------|-------------|
| ai_lab:federation_guard_events_rate5m | Rate of all federation guard events |
| ai_lab:evidence_replay_rate5m | Rate of evidence replay/invalid events |
| ai_lab:slo_violations_rate5m | Rate of SLO violations |
| ai_lab:architecture_risk_score | Weighted architecture risk (0-100) |
| ai_lab:runtime_health_score | Normalized runtime health (0-1) |
