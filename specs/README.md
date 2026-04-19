# Specs

Design specs for implementations. Specs describe **what** to build and **what contracts** it must honor. They do not prescribe language, framework, or package layout — those are implementer decisions.

Every spec is versioned. Spec version is logged in the implementation's build or run output.

## Current specs

| File | Implementation | Status |
|---|---|---|
| `grader-v0.2.md` | `/grader` | Ready for build |

## Adding a spec

- Name format: `{implementation-name}-v{major}.{minor}.md`.
- Major version bumps on breaking contract changes.
- Minor version bumps on additive changes.
- Supersede older versions by leaving them in place and updating the index. Do not delete.
