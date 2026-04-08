# GraphReview Report

## Executive Summary
- Source root: /home/lightdesk/Downloads/Projects/NodeAudit/Tests
- Episode id: all
- Modules in scope: 1
- Confidence score: 0.513
- Precision: 0.304 | Recall: 1.000 | F1: 0.467
- Security coverage: 0.000 | Dependency attribution validity: 0.000
- Stage coverage: 1.000
- LLM first-catch rate: 0.000
- LLM any-match rate: 1.000

## Security Analysis
## Cascade Attribution Summary
## Module Reviews
### bfs
- Status: changes_requested
- Summary: exports: [main()->None] | issues: 7 | depends_on: [breadth_first_search, breadth_first_search.breadth_first_search, node, node.Node]
- Shape: functions=main
- Findings: 7
- Reviews: 47
- Latest review: step 16 action=REQUEST_CHANGES reward=0.20

## RL Integrity
- Trajectory reconstructable from DB annotations and episode records.
- Reward causality linked to each persisted action payload.
- Easy/Medium deterministic replay expected; Hard constrained by temperature=0 judge policy.
