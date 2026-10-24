# Sequencer

The Sequencer is a Dashboard extension letting a user chain actions on the instruments of the Dashboard
(move actuators, grab detectors, wait, loop, branch...) without writing code.

## Language

**Sequencer**:
The extension launched from the Dashboard, with its user interface. It holds one or several **Sequences**.

**Sequence**:
A named, ordered tree of **Elements** that can be edited, saved to and loaded from a file, and executed.
One Sequence is displayed in each dock of the Sequencer.

**Element**:
One node of a Sequence, performing a single action when executed. Some Elements (containers, such as
repeat or choice) can have children Elements, the others cannot.

**Container**:
An Element that can have children, for instance *repeat* or *choice*.

**Sequence Element**:
The Element that executes another Sequence of the same Sequencer. It is never allowed to run the Sequence it
belongs to.

**State Element**:
The Element that applies a state saved by the **StateManager** (one per experiment).

**State**:
A state of the finite state machine driving the execution of a Sequence or of an Element (running, done...).
It is not a StateManager state: see **State Element** for that.

**Add button**:
The placeholder child shown at the end of the Sequence and of each Container, used to add an Element. It is
not part of the content of a Sequence and is never saved.

## Relationships

- A **Sequencer** contains one or more **Sequences**.
- A **Sequence** has a root Element, which owns the top level **Elements**.
- Only a **Container** has children **Elements**.
- A **Sequence Element** refers to another **Sequence** by its title.
