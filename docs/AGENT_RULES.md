# CommShield Agent Rules

All autonomous agents and contributors working on CommShield must strictly adhere to these rules:

1. **Source of Truth Priority**: Read `docs/ARCHITECTURE.md` and `docs/CONTRACTS.md` before coding. They are the source of truth.
2. **Strict Scope Control**: Edit only files named in the task. Never rewrite working files or reformat unrelated code.
3. **Contract Stability**: Do not change API, ML, or database contracts without asking.
4. **Empirical Integrity**: No hard-coded experiment results: all numbers come from real pipeline runs.
5. **Runtime Segregation**: Frontend never runs ML. Backend and `ml_engine` are Python.
6. **UI Layout Constraints**: Frontend: `h-screen` layout, full-height fixed sidebar, colour tokens from the design.
7. **Post-Task Completion Protocol**: After finishing: run relevant tests, then reply in at most 5 lines, no code in chat.
