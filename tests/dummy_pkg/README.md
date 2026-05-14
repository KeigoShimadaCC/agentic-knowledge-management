# dummy_pkg

Placeholder Python package so the `tests` workspace builds under Hatchling.
The `tests` project ships no production code; this package satisfies
`[tool.hatch.build.targets.wheel] packages` so `uv` can resolve the workspace
member. Do not import from it. Do not add code here.
