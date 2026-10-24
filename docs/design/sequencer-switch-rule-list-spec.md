# Redesign SwitchElt as a condition-first Rule list (generalizes ChoiceElt, replaces SwitchModelBase)

Not published to the issue tracker by request - kept here as the spec of record for
implementation on `feature/sequencer-switch-rule-list`. See `GLOSSARY.md` and
`docs/adr/0001-switchelt-rule-list.md` in `packages/pymodaq/src/pymodaq/extensions/sequencer/`
for the vocabulary and rationale this spec assumes.

## Problem Statement

As it stood on the (unreleased, now superseded) `feature/sequencer-manual-switch-v2` branch,
`SwitchElt` generalized `ChoiceElt`'s True/False branching to N outcomes via a dedicated
`SwitchModelBase`/`SwitchModelFactory` ecosystem (`BandsSwitchModel`: N-1 numeric boundaries →
N bands; `ManualSwitchModel`: N hand-picked named outcomes). In practice this was hard to use:
a boundary row's title visually collided with its own value ("Boundary 0" next to the value
`0`), the band labels that would explain what each boundary actually does never surfaced
anywhere near the boundary that produces them, and the id-stability machinery that kept branch
targets correct across edits existed to solve a case - reconfiguring outcomes after their
targets are already wired - that rarely comes up in practice, at real ongoing complexity cost.
None of this has shipped, so there's no backward-compatibility cost to replacing it.

## Solution

Replace the outcome-first `SwitchModelBase` model with a condition-first Rule list: an ordered
sequence of (condition, target) Rules, evaluated top to bottom, first matching condition wins,
with a mandatory always-matching fallback Rule guaranteeing every evaluation resolves to
exactly one target. Each Rule's condition is a plain, already-existing `ChoiceModelBase`
instance (True/False/Threshold/UserInput/Composite) - the same pluggable condition family
`ChoiceElt` and `WhileElt` already use via `ConditionHolder`, reused completely unmodified, one
instance per Rule instead of one per element. `ChoiceElt` becomes the permanently-locked
2-Rule case of this list (one pluggable condition Rule plus the fallback), with no add/remove
UI, so its public shape and saved-sequence format are unaffected. A separate, element-level
manual override lets a user force a specific target by hand, bypassing Rule evaluation
entirely, replacing what `ManualSwitchModel` provided.

## User Stories

1. As a sequence designer, I want to branch a sequence to one of several possible next elements
   based on a condition, so that I can build decision logic without nesting multiple
   `ChoiceElt`s.
2. As a sequence designer, I want each branch's condition to be any of the existing pluggable
   condition types (True/False/Threshold/UserInput/Composite), so that I don't have to learn a
   second, parallel condition system for N-way branching.
3. As a sequence designer, I want to see a branch's condition and its target together in the
   same place, so that I don't have to cross-reference two separate panels to understand what a
   branch does.
4. As a sequence designer, I want branches evaluated in a clear, predictable order (first match
   wins), so that I can reason about which branch fires without ambiguity.
5. As a sequence designer, I want every `SwitchElt` to always resolve to exactly one target, so
   that a sequence never gets stuck with "nothing matched."
6. As a sequence designer, I want to be warned if two of my branches could match at the same
   time, so that I catch likely condition-overlap mistakes before running the sequence.
7. As a sequence designer, I want to add a new branch rule to a `SwitchElt` at any time, so that
   I can grow my decision logic incrementally.
8. As a sequence designer, I want to remove a branch rule, so that I can simplify decision logic
   I no longer need.
9. As a sequence designer, I want a brand-new `SwitchElt` to start in a minimal, valid-looking
   state (just the fallback), so that I'm not forced to configure anything I don't need,
   mirroring how a new `ChoiceElt` already defaults to the trivial `'false'` condition.
10. As a sequence designer, I want to force a `SwitchElt` straight to a chosen target by hand,
    bypassing its rules, so that I can test or build the rest of a sequence without configuring
    real conditions first.
11. As a sequence designer, I want my saved sequences to round-trip a `SwitchElt`'s rules and
    their order exactly, so that reloading a sequence reproduces the same branching behavior.
12. As a sequence designer using `ChoiceElt`, I want its behavior and saved format
    (`go_to_true`/`go_to_false`/`choice_model`) completely unaffected by this change, so that
    existing sequences and third-party `ChoiceModel` plugins keep working.
13. As a sequence designer using `WhileElt`, I want its condition picker completely unaffected
    by this change, so that loop behavior isn't disrupted by work on branching elements.
14. As a third-party plugin author who registered a `ChoiceModelBase` model, I want my model to
    keep working unchanged and now also be usable as a `SwitchElt` rule's condition, so that I
    get N-way branching support for free.
15. As a maintainer, I want `BandsSwitchModel`/`ManualSwitchModel`/`SwitchModelBase`/
    `SwitchModelFactory`/`BranchHolder`/`SwitchConditionHolder`/`AddableRowsGroupParameter`
    deleted outright (not deprecated), so that the codebase doesn't carry two parallel,
    never-shipped branching mechanisms.
16. As a maintainer, I want `check_set_is_valid` to name which rule(s) have an unresolved
    target, so that a broken sequence is easy to debug, consistent with `ChoiceElt`'s existing
    error messages.
17. As a maintainer, I want a regression test suite covering rule add/remove, evaluation order,
    the fallback's always-match guarantee, the overlap warning, save/load round-trip, and
    `ChoiceElt`'s locked-to-2-rules behavior, so that this redesign is as well-covered as the
    `SwitchModelBase` version it replaces.
18. As a sequence designer, I want the fallback rule visually distinct (no condition picker,
    since it always matches) but still showing a normal target combo, so that I'm not confused
    about why it has no configurable condition.

## Implementation Decisions

- `SwitchElt` holds an ordered list of Rules; each Rule owns one Condition (a
  `ConditionHolder`-managed `ChoiceModelBase` instance) and one Target (an element id or the
  existing `CONTINUE` sentinel), plus its own transition wired into the element's state machine
  under a stable id assigned when the Rule is created.
- Evaluation: walk Rules in list order, call each Rule's Condition's `evaluate()` (boolean, no
  side effect/emission) in turn; on the first `True`, resolve to that Rule's id and fire the
  transition. The fallback Rule's Condition is pinned to the existing `TrueChoiceModel`,
  guaranteeing a match.
- `BranchHolder`, `SwitchConditionHolder`, `SwitchModelBase`, `SwitchModelFactory`,
  `BandsSwitchModel`, `ManualSwitchModel`, and `AddableRowsGroupParameter` are deleted outright.
- `ConditionHolder`/`ConditionHolderBase` are unchanged; a Rule composes one `ConditionHolder`
  instance internally instead of an element composing exactly one.
- `ChoiceElt` subclasses `SwitchElt`, constructing exactly 2 Rules at initialization (one
  user-pluggable Condition Rule defaulting to the existing `'false'` model, plus the fallback)
  and not exposing add/remove-Rule affordances, so it cannot grow past 2 rows.
  `go_to_true`/`go_to_false`/`choice_model` remain real properties on `ChoiceElt`, backed by
  its 2 Rules, so its saved-sequence format and the `ChoiceModelFactory` third-party entry
  point contract are unaffected.
- Manual override: a separate, element-level toggle (not a Rule, not a Condition) that, when
  active, resolves execution straight to a chosen target without evaluating any Rule.
- `check_set_is_valid`: every Rule's target must resolve to a real element (or `CONTINUE`);
  additionally, when more than one non-fallback Rule's condition currently evaluates `True`,
  surface a warning (not a hard error) naming the conflicting rules, since this usually
  indicates overlapping conditions.
- Rule add/remove is supported for v1; reordering rules is explicitly deferred.
- UI: each Rule renders as one self-contained row (its own small container, so
  `ConditionHolder.create_widget`'s fixed-index insertion doesn't collide across rules) showing
  its condition picker + param tree and its target combo together, in a dedicated
  addable/removable widget rather than a pyqtgraph `GroupParameter` row list. The fallback
  Rule's row shows no condition picker, consistent with how the existing `CONTINUE` target
  sentinel is already shown as a plain, unlabeled, always-available choice rather than a fake
  condition.
- Rationale and vocabulary are recorded in ADR 0001 and the sequencer's `GLOSSARY.md` (terms:
  Rule, Fallback rule, Condition, Target, Manual override).

## Testing Decisions

- Single seam: each affected element's public API, exercised with `pytest-qt`, matching the
  existing style in `sequencer_test.py` (`TestChoiceElt`, `TestWhileElt`, `TestGroupElt` are
  the direct prior art).
- Tests drive elements through their public surface and assert on observable behavior (which
  transitions fire, what `check_set_is_valid` raises/warns, what `to_dict_custom`/
  `from_dict_custom` round-trips to, widget child counts after `create_widget()`) rather than
  reaching into `Rule`'s internals directly.
- Coverage carried forward conceptually from the deleted `SwitchModelBase`-era tests: save/load
  round-trip, `check_set_is_valid` naming the broken rule, and live-widget refresh when a rule
  is added/removed while its editor is open. Not carried forward: anything about preserving a
  target's id across an outcome-set change - Rule's atomicity (condition and target added/
  removed together) makes that scenario structurally impossible rather than something to test
  for.

## Out of Scope

- Rule reordering (drag/move).
- Any change to the `feature/sequencer-graph-view-readonly` branch: it hard-codes `ChoiceElt`'s
  exact 2-output shape via a dedicated `_ChoiceNodeModel`, and has no handling at all for
  `SwitchElt` today (falls through to the generic single-successor `_LeafNodeModel`) - a
  pre-existing gap this redesign doesn't create or worsen. Extending the graph view for N-way
  `SwitchElt` branches is separate follow-up work.
- Reimplementing `BandsSwitchModel`'s/`ManualSwitchModel`'s specific behavior as presets/
  helpers that generate Rules automatically - a user composes Rules by hand from existing
  `ChoiceModelBase` types instead.
- Any change to `ChoiceModelBase`, `ChoiceModelFactory`, `ConditionHolder`,
  `ConditionHolderBase`, `WhileElt`, or any existing concrete choice model - all reused
  unmodified.
- A combinator for "more than one matching condition drives a single composite outcome" -
  rejected in ADR 0001; overlap only ever produces a diagnostic warning, never a different
  execution path.

## Further Notes

- This spec supersedes and deletes the `SwitchElt`/`SwitchModelBase` work built on
  `feature/sequencer-manual-switch-v2`. None of it has merged to `upstream/dev` or shipped in a
  release, so this is a clean replacement, not a migration.
- Implementation happens on `feature/sequencer-switch-rule-list`, branched fresh off
  `upstream/dev` rather than continuing `feature/sequencer-manual-switch-v2`, since most of
  that branch's content is what's being deleted.
- Not published to the issue tracker by request - this file is the spec of record.
