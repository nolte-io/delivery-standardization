# Jira Workflow Rules

These rules enforce the Nolte delivery workflow at the transition level.
They complement the grader (which scores retrospectively) by preventing
non-compliant transitions in real time.

---

## Rule 1 — Block In Implementation without Done Specifying

**What it prevents:** A story being moved to In Implementation without having
gone through the spec workflow (i.e., In Specification → Done Specifying first).
This is what the grader grades as W1=FAIL.

**Where to create it:** Jira > Project Settings > Automation > Create rule

### Configuration

| Field | Value |
|-------|-------|
| Trigger | Issue transitioned |
| From status | *Any status* |
| To status | In Implementation |

**Condition — Advanced compare:**
```
{{issue.status.name}} == "In Implementation"
AND NOT issue.changelog contains status "Done Specifying"
```

> Note: Jira's native automation does not have a built-in "was previously in status X" condition. Use the **Advanced Compare** condition with `issue.changelog` or add a ScriptRunner condition. If using native automation without ScriptRunner, use the workaround below.

**Native automation workaround (no ScriptRunner):**
Use a required field validator instead. Add a workflow transition screen to
`* → In Implementation` that requires the **Spec Approver** field to be set.
Since Spec Approver is only set at the Done Specifying gate, a missing value
is a reliable proxy for a bypassed workflow.

| Field | Value |
|-------|-------|
| Transition screen | "Commitment Gate" |
| Required field | Spec Approver (User Picker) |
| Validator message | "Spec Approver must be set. This field is populated at the Done Specifying → In Implementation gate. Move the story through Done Specifying first." |

---

### Automation rule — comment and revert on bypass (ScriptRunner / Advanced)

**Trigger:** Issue transitioned to In Implementation

**Condition:** `issue.changelog` does NOT contain status "Done Specifying"

**Actions (in order):**
1. Transition issue → Awaiting Specification
2. Add comment (see copy below)

---

### Comment copy — posted to bypassed issues

> **Workflow bypass detected — action required**
>
> This story was moved to **In Implementation** without going through
> **Done Specifying**. The commitment gate was skipped.
>
> What this means:
> - No spec approval was recorded
> - No BDD baseline exists at the commitment point
> - Cycle time and quality metrics cannot be accurately measured for this story
>
> **Next steps:**
> 1. Move the story back through **In Specification**
> 2. Complete the spec template (Business Objective, AC, Scenarios, Risks)
> 3. Get approval from an authorized Spec Approver
> 4. Transition through **Done Specifying** → **In Implementation**
>
> If this story genuinely required emergency implementation (no spec possible),
> escalate to the Head of Engineering for a manual override and retroactive
> documentation.

---

## Rule 2 — Require Spec Approver at Done Specifying gate

**What it prevents:** Moving to In Implementation without an authorized approver
recorded. This is what the grader grades as C3=FAIL.

**Where to create it:** Jira > Project Settings > Workflows > Edit workflow >
transition "Done Specifying → In Implementation" > Validators

### Validator configuration

| Field | Value |
|-------|-------|
| Validator type | Field Required |
| Field | Spec Approver |
| Error message | "Spec Approver must be set before committing to implementation. An authorized approver (Head of Engineering or Head of Product delegate) must sign off on the spec." |

---

## Rule 3 — Prevent backward transitions without comment

**What it prevents:** Moving a story backward in the kanban flow (e.g.,
In Implementation → In Specification) without documenting why.
This is what the grader grades as D10=FAIL.

**Backward transitions that require justification:**
- In Implementation → In Specification / Done Specifying / Awaiting Specification
- Done Implementing → In Implementation
- In Validation → Done Implementing / In Implementation

**Automation rule:**

| Field | Value |
|-------|-------|
| Trigger | Issue transitioned |
| Condition | Transition is a backward kanban move (to-status rank < from-status rank) |
| Action | Require comment on the transition screen: "Reason for returning this story" (plain text, required) |

> Use the transition screen "Backward Move" with a mandatory Comment field.
> Jira's native screen configuration supports this without ScriptRunner.

---

## Implementation order

1. **Rule 2** (Spec Approver required at gate) — lowest risk, pure field validator,
   no automation needed. Do this first.
2. **Rule 1** (block bypass, comment on revert) — requires testing in a staging
   project before enabling in production boards. Start with BBIT or SCPG as the
   pilot.
3. **Rule 3** (backward transition comment) — workflow screen change, low risk.
   Enable alongside Rule 1.

---

## Verification

After enabling each rule, run the grader for the next 2-week window. Confirm:
- W1 fail rate drops to 0% (Rule 1 working)
- C3 fail rate drops significantly (Rule 2 working)
- D10 fail rate drops or documented bypasses increase (Rule 3 working — failures
  should still appear in the grader but now have documented rationale)
