# PyMoDAQ Sequencer — Conditional Branching

Vocabulary for how a sequence branches to one of several possible next elements: `ChoiceElt`'s
fixed True/False case and `SwitchElt`'s general N-way case, and the pluggable conditions both
are built from.

## Language

**Rule**:
An ordered `(condition, target)` pair in a `SwitchElt`'s rule list. Rules are evaluated
top-to-bottom; the first rule whose condition matches determines the branch taken.
_Avoid_: Outcome, branch, case

**Fallback rule**:
The mandatory, always-last rule in a `SwitchElt`'s rule list, whose condition always matches -
guarantees every evaluation resolves to exactly one target, never "nothing matched."
_Avoid_: Default rule, else branch

**Condition**:
A pluggable, evaluatable piece of logic (`ChoiceModelBase`: True/False/Threshold/UserInput/
Composite, extensible via `ChoiceModelFactory`) that decides whether a rule matches. The same
family is reused by both `ChoiceElt` and every rule of a `SwitchElt`.
_Avoid_: SwitchModel, ChoiceModel (as the domain term - fine as a class name)

**Target**:
The id of the sequence element a rule points to when it's the first to match, or `CONTINUE`
("wherever this element would go next anyway").
_Avoid_: Branch target (fine as an implementation name, e.g. `go_to`), go-to

**Manual override**:
An element-level toggle that forces a `SwitchElt` straight to a chosen target, bypassing rule
evaluation entirely - for forcing a branch while building or testing a sequence. Independent of
the rule list: not itself a condition or a rule.
_Avoid_: ManualSwitchModel (retired - this was the old mechanism, now superseded by an
element-level feature rather than a condition type)
