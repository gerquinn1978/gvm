# Test Coverage Safety Net Checklist

Run through this checklist before finalizing the test case document. For each item, confirm it was covered during generation or note as N/A with reason.

---

## Traceability (North/BDD)

- [ ] Every requirement ID has at least one test case
- [ ] Every test case traces to at least one requirement ID
- [ ] No orphan tests (tests without a requirement reference)
- [ ] Must requirements have happy-path AND negative test cases
- [ ] Should requirements have at least happy-path test cases
- [ ] Could requirements have at least one test case

## Technique Coverage (Copeland)

- [ ] Requirements with conditional logic have decision table tests
- [ ] Requirements describing workflows have state transition tests
- [ ] Requirements with data inputs have equivalence class tests
- [ ] Requirements with numeric ranges have boundary value tests
- [ ] Requirements with multiple interacting parameters have pairwise tests
- [ ] Complex conditional logic analyzed with cause-effect graphing where decision tables are insufficient

## Thoroughness (Beizer)

- [ ] Boundary values tested for all numeric constraints (min, min-1, min+1, max-1, max, max+1)
- [ ] Invalid equivalence classes covered (not just valid inputs)
- [ ] Empty/null/missing inputs tested where applicable
- [ ] Error guessing applied to complex or fragile areas
- [ ] Off-by-one scenarios covered for counts and ranges

## Consumer App Realism (Kaner)

- [ ] First-time user / empty state tested
- [ ] Interrupted workflows tested (back, refresh, close mid-process)
- [ ] Realistic data volumes considered (not just trivial test data)
- [ ] Platform-specific behaviours considered (if multi-platform)
- [ ] Implicit requirements tested (no crash, no data loss, responsive)
- [ ] Error messages are user-facing and helpful (not technical dumps)

## Risk Alignment (Kaner)

- [ ] Must requirements have the most thorough test coverage
- [ ] High-severity failure scenarios are tested regardless of priority
- [ ] Test priorities are consistent with requirement priorities
- [ ] Edge case tests deprioritized appropriately (not all at Must level)

## Health Report Items

- [ ] All untestable requirements either fixed or acknowledged in decisions file
- [ ] All inconsistencies either resolved or acknowledged
- [ ] Acknowledged decisions file is up to date

## Final Quality Gate

- [ ] Test case IDs are unique and follow the TC-{REQ-ID}-{NN} convention
- [ ] Every test has a descriptive name (behaviour, not mechanism)
- [ ] Given/When/Then uses concrete values, not abstract descriptions
- [ ] Complex scenarios have traditional detail (preconditions, steps, expected results)
- [ ] Traceability matrix is complete and accurate
- [ ] HTML and MD versions are in sync
