# Evidence Grounding Policy

The runtime MUST distinguish between:

- verified evidence
- inference
- assumptions
- unknowns

Rules:

1. Never claim files, configs, logs, containers or ports exist unless present in:
   - tool output
   - semantic memory
   - user prompt

2. If evidence is missing, explicitly say:
   - "No evidence found"
   - "Unable to verify"
   - "Hypothesis only"

3. Prefer:
   - observed facts
   - command outputs
   - logs
   - inspect results

4. Separate:
   - FACT
   - HYPOTHESIS
   - RECOMMENDATION

5. Never invent:
   - YAML configs
   - docker labels
   - filesystem paths
   - services
   - network names
   - ports
