# Jira Story Template

Copy-paste this template into Jira's Story issue type description template. Every new Story uses this structure.

When any section is not applicable, do not delete the header. Write "None identified" or "N/A — [brief reason]" so the grader sees explicit intent rather than a missing section.

---

## Template

```markdown
## Business Objective
(Link to Epic. Describe the outcome in business terms: revenue, retention, activation, risk reduction, cost savings, time savings, or compliance. Name the mechanism.)

Example:
"Reduce P50 claim intake time from 8min to <3min to handle 30% more claim volume without adding headcount."

## Observable Impact
(One sentence. The metric, the threshold, and either the measurement location or the observability mechanism. This is how we will know the work landed.)

Example:
"P50 claim intake time drops from 8min to <3min in Datadog dashboard X, observed within 2 weeks of release."

## Acceptance Criteria
(Plain language. Verifiable by a non-engineer. Written before implementation.)

Example:
- When a broker submits a quote request, a confirmation email arrives within 60 seconds.
- When a required field is missing, the form displays a specific error next to that field.
- When a submission completes, the record appears in the broker's intake queue within 2 minutes.

## Scenarios
(BDD Given/When/Then covering the highest-value rules. Not every rule — the core behavior.)

Example:
Given a broker has completed all required fields
When they submit the quote request form
Then a confirmation email is sent within 60 seconds
And the record appears in the broker intake queue within 2 minutes

## Risks
(Regulatory, technical, dependency, data. "None identified" is allowed and must be explicit. Blank is not.)

Example:
- Regulatory: form captures PII, needs privacy review before launch
- Dependency: intake queue API rate limits — confirm capacity at expected volume
```

---

## Rules for using the template

- **Never delete a section header.** The grader looks for each by name. A missing section fails that dimension.
- **"None identified" is a valid answer** for Risks and for Observable Impact (if the work is a non-user-facing operational task). It is not valid for Business Objective, AC, or Scenarios.
- **Write AC before scenarios, and both before commitment.** AC edits after commitment fail U7 (no scope evolution).
- **For operational Tasks (rare):** only the Business Objective and Observable Impact sections are required. AC and Scenarios can be minimal. Risks are still required.
