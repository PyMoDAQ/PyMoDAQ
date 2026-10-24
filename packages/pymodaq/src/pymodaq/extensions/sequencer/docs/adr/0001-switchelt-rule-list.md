---
status: accepted
---

# SwitchElt branches on an ordered Rule list, not a pluggable SwitchModel

`SwitchElt` (unreleased, built this week) originally generalized `ChoiceElt`'s True/False with
its own parallel model ecosystem: `SwitchModelBase`/`SwitchModelFactory`, with concrete models
`BandsSwitchModel` (N-1 numeric boundaries → N bands) and `ManualSwitchModel` (N hand-picked
named outcomes). In practice this UI proved confusing (a boundary row's title visually
collided with its value, and the computed band labels never surfaced anywhere near the
boundary that produced them), and the underlying id-stability machinery it required
(`BranchHolder.rebuild()`/`reset()` preserving targets by numeric outcome id across add/
remove/model-swap) turned out to solve a case - editing outcomes after already wiring their
targets - that rarely happens in practice.

We're replacing it with a `Rule` list: an ordered sequence of `(condition, target)` pairs,
evaluated top-to-bottom, first matching condition wins, with a mandatory always-matching
fallback rule (condition pinned to the existing `TrueChoiceModel`) guaranteeing every
evaluation resolves to exactly one target. Each rule's condition is a plain `ChoiceModelBase`
instance - the same True/False/Threshold/UserInput/Composite family `ChoiceElt` already uses,
via one `ConditionHolder` per rule, reused completely unmodified (confirmed: `WhileElt`, from
the just-merged #1346, already depends on `ConditionHolder` standalone, with no `BranchHolder`
involved, so it was never safe to fold into something SwitchElt-specific anyway).

`ChoiceElt` becomes the permanently-locked 2-rule case of this list (one user-pluggable
condition rule, plus the fallback) - no add/remove UI, so it can't silently grow past 2 rows.
Its saved-sequence format (`go_to_true`/`go_to_false`/`choice_model`) and the
`ChoiceModelFactory` third-party entry point contract are unaffected either way.

## Considered options

- **Outcome-first** (define named outcomes, attach conditions to each): rejected - needs its
  own combinator for "multiple conditions on one outcome" and a tie-break rule for
  simultaneous matches, neither of which a condition-first list needs (shared targets are just
  two rules pointing at the same place; evaluation order is the tie-break).
- **Collect every matching condition as a ranked list**, rather than first-match-wins: rejected
  for the engine's actual transition - `SwitchElt` runs on `QStateMachine`, which can only be
  in one state at a time, so there's always exactly one target taken regardless. Kept as a
  `check_set_is_valid` diagnostic instead: warn when more than one non-fallback rule matches
  the same evaluation (almost always an authoring mistake, e.g. overlapping thresholds).
- **Keep `SwitchModelBase` as a separate, parallel condition ecosystem**: rejected - it
  duplicated `ChoiceModelBase`'s shape for no real gain once conditions live per-rule instead
  of per-element, and kept two factories/two sets of concrete models to maintain instead of one.

## Consequences

- `BranchHolder` (the id-keyed dict, `rebuild()`/`reset()`, stable-id preservation, live-widget
  refresh - all written this week) is retired entirely: each `Rule` owns its condition and
  target together, so removing a rule removes both at once, with no separate "does the target
  survive" question to answer.
- `SwitchConditionHolder`, `SwitchModelBase`, `SwitchModelFactory`, `BandsSwitchModel`,
  `ManualSwitchModel`, and `AddableRowsGroupParameter` (the GroupParameter-row UI backing the
  old Boundaries/Outcomes lists) are all retired - none of this ever shipped, so there's no
  deprecation/back-compat path needed, just deletion.
- `ConditionHolder`/`ConditionHolderBase` are unchanged and gain a second use site (one
  instance per `Rule`, instead of one per element) alongside their existing use by `ChoiceElt`
  and `WhileElt`.
- "Manual override" (force a specific target by hand, bypassing evaluation) survives as a
  separate element-level toggle, not a rule or a condition type.
