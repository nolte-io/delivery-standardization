# Jira Custom Fields — Creation Checklist

Four custom fields. Create once, apply to the Story issue type and the Story screen. The grader discovers field IDs by name, so the exact name matters — do not abbreviate or change capitalization.

## Fields

### 1. Design Artifact Link

- **Name:** `Design Artifact Link`
- **Type:** URL (supports multiple values, or text with multiple URLs if multi-URL type is unavailable)
- **Purpose:** Engineering links design artifacts — architecture diagrams, frontend mockups, UI specs, etc.
- **Required at:** In Implementation → Done Implementing for non-trivial Stories (judge-determined, not enforced by workflow).
- **Graded by:** D2.

### 2. Production Release Reference

- **Name:** `Production Release Reference`
- **Type:** URL or short text (accepts deploy URLs, release tags, or merged PR links)
- **Purpose:** Evidence that the work is live in production.
- **Required at:** Done Implementing and Done.
- **Graded by:** Y5, D6.

### 3. Impact Measurement Link

- **Name:** `Impact Measurement Link`
- **Type:** URL
- **Purpose:** Link to the dashboard, query, or document where impact will be observed post-release.
- **Required at:** Done transition.
- **Graded by:** U10.

### 4. Spec Approver

- **Name:** `Spec Approver`
- **Type:** User picker (single user)
- **Purpose:** Records who approved the Story at the Done Specifying → Ready gate.
- **Required at:** Done Specifying → Ready transition. Jira workflow should enforce this — transition not allowed if field is empty.
- **Graded by:** C3.
- **Authorized approvers** (configured in grader, per project): Head of Engineering and delegates; Nolte POC when Nolte is trusted Product Owner; client POC when ownership sits with client.

## Configuration steps

1. In Jira settings, go to **Issues → Custom Fields**.
2. For each field above: **Add custom field → Select type → Name exactly as specified**.
3. Associate each field with the Story issue type (and Task, Bug if relevant).
4. Add each field to the Story screen and the Edit screen.
5. For Spec Approver, configure workflow validator: transition `Done Specifying → Ready` requires Spec Approver to be populated.
6. Optionally, add Production Release Reference as a workflow validator on `Done Implementing → In Validation`.

## Verification

After creation, run this JQL to confirm fields are queryable:

```
project = PROJ AND "Spec Approver" is not EMPTY
project = PROJ AND "Production Release Reference" is not EMPTY
```

Both queries should return 0 results initially (no Stories have populated them yet). Both should be valid JQL (no "unknown field" error).

## Retroactive application

Existing Stories are not backfilled. The grader evaluates these fields only on Stories created after field creation. Historical grading will show `FIELD_EMPTY` for older Stories, which is expected.

## When Yanna talks to Jira admin

One meeting creates all four fields plus the workflow validator. Do not spread this across multiple cycles — the grader does not run cleanly until all four exist.
