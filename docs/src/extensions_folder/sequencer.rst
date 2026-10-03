.. _sequencer_extension:

Sequencer
=========

.. _sequencer_main_fig:

.. figure:: sequencer_data/sequencer_main.png
   :alt: sequencer
   :width: 100%

   The Sequencer extension with two sequences: the *main* one (left) calling a second one (right).


Introduction
++++++++++++

The :ref:`DAQ_Scan_module` is perfect when you want to acquire data on a regular grid of actuators positions. But an
experiment is often more of a *procedure*: move some stages to a starting point, wait for a temperature to settle,
take a few snapshots, check a signal level and, depending on its value, go back a few steps or move on to the next
configuration of your setup...

The Sequencer allows you to build such procedures graphically, without writing any code. A sequence is a tree of
**elements** (move actuators, grab detectors, wait, repeat, scan, choose where to go next, apply a Dashboard state,
call another sequence...) executed one after the other. Some elements (Repeat, Scanner) are *containers*: they execute
their children elements one or several times. Under the hood, each sequence is executed by a Qt state machine, so the
GUI is never blocked and a running sequence can be paused, resumed or stopped at any time.

All the data produced while running (detectors data, actuators positions) can be logged in a h5 file, with time stamps,
the same way as the :ref:`DAQ_Logger <DAQ_Logger_module>` does.

Sequences can be saved in human readable files (``.seq``) and loaded back later.


Launching the Sequencer
+++++++++++++++++++++++

Like the other extensions, the Sequencer is started from the *Extensions* menu of the :ref:`Dashboard_module`. It
then acts on the actuators and detectors declared in the Dashboard.

It can also be started on its own by running the ``sequencer.py`` module. A Dashboard is created under the hood and
the command line arguments of the Dashboard can be used, for instance to load an experiment at startup:

.. code-block:: bash

   python -m pymodaq.extensions.sequencer.sequencer -x my_experiment

.. note::

   Some elements (Grab, Choice with the threshold model, State) rely on the modules and states of the Dashboard. An
   :ref:`Experiment <experiment_manager>` should therefore be applied in the Dashboard before using them, and the
   State element needs some entries defined in the :ref:`state_manager`.


The User Interface
++++++++++++++++++

Main toolbar
------------

The main window (see :numref:`sequencer_main_fig`) has a toolbar with:

* the h5 file actions: select/create the h5 file where data will be logged, and show the saving settings
* the Dashboard actions, to show/hide the Dashboard and its modules
* **Add Sequence** / **Remove Sequence**: add a new sequence panel, or remove the last one (the *main* one cannot be
  removed)
* **Load Sequence** / **Save Sequence**: load or save *all* the sequences from/to a ``.seq`` file
* the workflow actions:

  * **Start**: starts the *main* sequence (the first panel). The other sequences are only executed when called by a
    :ref:`Sequence element <sequencer_elt_sequence>`
  * **Stop**: stops all sequences
  * **Pause**: pauses/resumes all sequences
  * **Log**: if checked when starting, all data produced while running are logged in the h5 file, see
    :ref:`sequencer_logging`

Sequence panels
---------------

Each sequence is displayed in its own panel with:

* an editable name (press *Enter* to validate). Other elements referring to this sequence are updated accordingly
* its own **Start**, **Stop** and **Pause** buttons, to execute only this sequence
* the tree of elements
* a status bar displaying the element currently executed

Editing a sequence
------------------

.. _sequencer_add_element_fig:

.. figure:: sequencer_data/sequencer_add_element.png
   :alt: add element
   :width: 60%

   Adding an element using the *Add Element* button at the end of a level of the tree.

Elements are added using the **Add Element** button displayed at the end of each level of the tree (see
:numref:`sequencer_add_element_fig`): at the root of the sequence and inside each container element. The tree also
has a context menu (right click) to:

* **Add Element**: inserts the element after the selected one, or as the first child if the selected element is a
  container
* **Remove Element** (*Del* key): removes the selected element (and its children)
* **Clear Children**: removes all the elements at the level of the selected element (or all its children for a
  container)
* **Load Sequence File** (*Ctrl+O*) / **Save Sequence File** (*Ctrl+S*): load or save only *this* sequence

Elements can be reordered or moved into/out of containers using drag and drop.

Each element is displayed with:

* its **id**: a unique integer used by the :ref:`Choice element <sequencer_elt_choice>` to select where to jump
* its type and a summary of its configuration
* an **Execute** button, to execute this element on its own (useful to test it)

**Double clicking** on an element opens its editor as a popup window. The editors of each element are described below.
Close the popup (click outside or press *Enter*) to validate the changes.


.. _sequencer_elements:

The Elements
++++++++++++

.. _sequencer_elt_move:

Move
----

.. _sequencer_elt_move_fig:

.. figure:: sequencer_data/elt_move.png
   :alt: move element
   :width: 50%

   The Move element editor with two actuators.

Moves one or several actuators of the Dashboard to absolute values. In the editor (:numref:`sequencer_elt_move_fig`),
use the *Add* button to select the actuators to be moved and set their target values. The units are the ones of each
actuator.

The **hourglass** button sets whether the element should wait for all the moves to be done before moving on to the
next element (default) or should move on immediately. Once the moves are done, the reached positions are logged.

.. _sequencer_elt_grab:

Grab
----

.. _sequencer_elt_grab_fig:

.. figure:: sequencer_data/elt_grab.png
   :alt: grab element
   :width: 50%

   The Grab element editor.

Acquires data from one or several detectors, selected using the check boxes of the editor
(:numref:`sequencer_elt_grab_fig`). Three modes are available from the toolbar:

* **Snap**: triggers a single acquisition on all selected detectors and waits for all of them to have finished. The
  data are logged and the sequence moves on
* **Grab**: starts a continuous acquisition on the selected detectors and moves on immediately. Each acquired data
  will be logged until the detectors are stopped
* **Stop**: stops any continuous acquisition on the selected detectors

.. _sequencer_elt_wait:

Wait
----

.. _sequencer_elt_wait_fig:

.. figure:: sequencer_data/elt_wait.png
   :alt: wait element
   :width: 40%

   The Wait element editor.

Waits for a given time, in milliseconds (:numref:`sequencer_elt_wait_fig`), before moving on to the next element.

.. _sequencer_elt_repeat:

Repeat
------

.. _sequencer_elt_repeat_fig:

.. figure:: sequencer_data/elt_repeat.png
   :alt: repeat element
   :width: 40%

   The Repeat element editor.

A container element: executes all its children a given number of times (:numref:`sequencer_elt_repeat_fig`), then
moves on to the next element.

.. _sequencer_elt_scanner:

Scanner
-------

.. _sequencer_elt_scanner_fig:

.. figure:: sequencer_data/elt_scanner.png
   :alt: scanner element
   :width: 60%

   The Scanner element editor.

A container element embedding the same Scanner as the DAQ_Scan, see :ref:`scanner_paragraph`. Select the actuators
and the scan type and settings in the editor (:numref:`sequencer_elt_scanner_fig`). When executed, for each step of the
scan the element moves the actuators, logs their positions, then executes all its children. Once the last step is
done, the sequence moves on to the next element. The current step is displayed in the element summary.

This allows to build scans with arbitrary actions at each step: a snap with some detectors, a wait, a nested scan,
a different detector configuration through a State element...

.. _sequencer_elt_choice:

Choice
------

.. _sequencer_elt_choice_fig:

.. figure:: sequencer_data/elt_choice.png
   :alt: choice element
   :width: 50%

   The Choice element editor using the threshold model.

The Choice element is what makes a sequence more than a list of actions: it evaluates a condition and jumps to one
element if the result is *True* and to another one if it is *False*. The two target elements are selected by their id
in the green (*True*) and red (*False*) combo boxes of the editor (:numref:`sequencer_elt_choice_fig`). Any element of
the sequence can be a target, before or after the Choice element: you can build loops (jump backward), branches
(jump forward) or early exits.

The condition is given by a **choice model**, selected in the editor. The models shipped with PyMoDAQ are:

* **true** / **false**: always jump to the True (resp. False) target. Useful for unconditional jumps (*go to*)
* **user_input**: opens a dialog asking the user to *Proceed* (True) or *Go back* (False)
* **threshold**: grabs data from the selected detectors and compares a scalar (0D) data to a threshold. Select the
  detectors, press *Probe Data* to get the list of available 0D data, select one of them, then set the threshold value
  and the direction: *Above* (True if the data is above the threshold) or *Below*

Other models can be written, see :ref:`sequencer_custom_choice_model`.

As an example, :numref:`sequencer_example_flow_fig` shows a sequence moving an actuator, taking three snapshots, and
checking a signal: if it is above the threshold, a new State is applied on the Dashboard, otherwise the procedure
starts again.

.. _sequencer_example_flow_fig:

.. graphviz::
   :caption: Execution flow of a sequence using a Choice element to loop back.
   :align: center

   digraph sequencer_example {
      rankdir=TB;
      compound=true;
      node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica", fontsize=11];
      edge [fontname="Helvetica", fontsize=10];

      move [label="1 - Move\nX axis to 0 mm"];
      subgraph cluster_repeat {
         label="2 - Repeat (3 times)"; style="rounded,dashed"; fontname="Helvetica"; fontsize=11;
         grab [label="3 - Grab\nSnap Det 0D"];
         wait [label="4 - Wait\n500 ms"];
         grab -> wait;
      }
      choice [label="5 - Choice\nmodel: threshold", shape=diamond, fillcolor="#fdf3e1"];
      state [label="6 - State\napply 'measurement'"];
      end [label="Sequence finished", shape=oval, fillcolor="#e9f6ec"];

      move -> grab [lhead=cluster_repeat];
      wait -> choice [ltail=cluster_repeat, label=" after 3 loops"];
      choice -> state [label=" True", color="#2e7d32", fontcolor="#2e7d32"];
      choice -> move [label=" False", color="#c62828", fontcolor="#c62828", constraint=false];
      state -> end;
   }

.. _sequencer_elt_sequence:

Sequence
--------

.. _sequencer_elt_sequence_fig:

.. figure:: sequencer_data/elt_sequence.png
   :alt: sequence element
   :width: 40%

   The Sequence element editor.

Executes another sequence, selected in the editor (:numref:`sequencer_elt_sequence_fig`) among the other panels of
the Sequencer (a sequence cannot call itself). The calling sequence moves on once the called one has finished.

This allows to split a long procedure into reusable blocks. If a called sequence is renamed, the elements calling it
are updated. If it is removed, they are set to another sequence and a warning is displayed so you can review them.

.. _sequencer_elt_state:

State
-----

.. _sequencer_elt_state_fig:

.. figure:: sequencer_data/elt_state.png
   :alt: state element
   :width: 50%

   The State element editor.

Applies one of the states defined in the :ref:`state_manager` of the Dashboard for the current experiment: actuators
positions, detectors and actuators settings... Select the state in the editor (:numref:`sequencer_elt_state_fig`); the
*Show Manager* button opens the State Manager to review or create states. The sequence moves on once the state has been
applied. The actuators moves triggered by the state are logged.


Running a sequence
++++++++++++++++++

When a sequence is started (from the main toolbar for the *main* sequence, or from its panel), all its elements are
first checked. If some are not valid (an actuator or a detector not available in the Dashboard, a missing Choice
target, no experiment applied...) the errors are written in the log and the status bar displays *Some elements are not
valid, check the log*: the sequence is not started.

While running, the element being executed is selected in the tree and displayed in the status bar.

* **Pause**: the sequence is paused as soon as possible. When resumed, the element that was running when paused is
  executed again from its start. The containers enclosing it keep their loop counters
* **Stop**: the sequence is stopped. Stopping from the main toolbar stops all sequences

.. _sequencer_logging:

Saving and logging
++++++++++++++++++

Data logging
------------

If the **Log** action is checked when the sequence is started, all data produced by the elements are saved in the h5
file selected using the file toolbar:

* the data snapped or grabbed by the Grab elements
* the actuators positions reached by the Move, Scanner and State elements

Each run creates a new node in the h5 file. Data are saved under the node of the control module that produced them,
with their time stamps, as done by the DAQ_Logger. The resulting file can be explored with the :ref:`H5Browser_module`.

Sequence files
--------------

Sequences are saved in ``.seq`` files, by default in the ``sequences`` folder of PyMoDAQ's configuration directory.
They are YAML files and can be read and edited with any text editor. Below is the file corresponding to the example of
:numref:`sequencer_example_flow_fig`:

.. code-block:: yaml

   sequences:
     main:                      # the name of the sequence (panel)
       elt_name: root
       id: -1
       children:
       - elt_name: move
         id: 1
         Xaxis: 0.0 mm          # actuator name: target value with units
         wait_move_done: true
       - elt_name: repeat
         id: 2
         n_repeat: 3
         children:              # elements within the Repeat container
         - elt_name: grab
           id: 3
           detectors: [Det 0D, Camera]
           selected: [Det 0D]
           status: Snap
         - elt_name: wait
           id: 4
           wait_time: 500       # in ms
       - elt_name: choice
         id: 5
         go_to_true: 6          # id of the target element if True
         go_to_false: 1         # id of the target element if False
         choice_model: threshold
         detectors: {all_items: [Det 0D, Camera], selected: [Det 0D]}
         threshold: 0.5
         directions: [Above, Below]
         direction: Above
         data_names: [Det 0D/CH00]
         data_name: Det 0D/CH00
       - elt_name: state
         id: 6
         state: measurement
         experiment: my_experiment
         states: [default, measurement]

The *Save Sequence* action of the main toolbar saves all the sequences under the ``sequences`` key. A file saved from
the context menu of a sequence panel contains only this sequence (its ``root`` element) and is loaded in a single
panel.


For developers
++++++++++++++

How it works
------------

Each element derives from the ``SeqEltBase`` class
(``pymodaq.extensions.sequencer.utilities.element_factory``) and owns a ``CompositeState`` (its ``mstate``
attribute), a Qt state made of three sub-states, see :numref:`sequencer_element_state_fig`:

* the ``execute_state``: when entered, the element ``execute`` method is called
* the ``children_state``: contains the composite states of the element's children (for container elements)
* the ``done_state``: a final state, ending this element

The element drives its state through Qt signals:

* ``done_signal``: the element has finished, the sequence moves on to the next element
* ``children_signal``: the children of a container element should be executed. Once the last child has finished,
  the ``execute_state`` is entered again so that the container decides whether to loop again (emitting
  ``children_signal``) or to finish (emitting ``done_signal``)
* ``go_to_signal``: used by the Choice element to jump to its True or False target
* ``data_to_log_signal``: emitted with the data to be logged (use the ``save_data`` method)

When a sequence is started, ``Sequence.recursive_connect_elts`` connects the composite states of all elements: the end
of an element leads to the next sibling, or back to its parent's ``execute_state`` for the last child. The Pause and
Stop actions are also connected to each element's state.

.. _sequencer_element_state_fig:

.. graphviz::
   :caption: The composite state of an element and its transitions.
   :align: center

   digraph element_state {
      rankdir=LR;
      compound=true;
      node [shape=box, style="rounded,filled", fillcolor="#eef3fb", fontname="Helvetica", fontsize=11];
      edge [fontname="Helvetica", fontsize=10];

      subgraph cluster_elt {
         label="CompositeState of an element (elt.mstate)"; style="rounded"; fontname="Helvetica"; fontsize=11;
         execute [label="execute_state\ncalls elt.execute()"];
         children [label="children_state\nchildren's CompositeStates"];
         done [label="done_state", shape=doublecircle, fillcolor="#e9f6ec", fontsize=10];
         execute -> children [label="children_signal"];
         children -> execute [label="last child finished"];
         execute -> done [label="done_signal"];
      }

      next [label="next sibling's\nCompositeState"];
      parent [label="parent's\nexecute_state"];
      interrupt [label="InterruptState\n(paused)", fillcolor="#fdf3e1"];
      stop [label="Sequence\nfinal state", shape=doublecircle, fillcolor="#fbe9e9", fontsize=10];

      done -> next [ltail=cluster_elt, label="finished\n(not the last child)"];
      done -> parent [ltail=cluster_elt, label="finished\n(last child)"];
      execute -> interrupt [ltail=cluster_elt, label="Pause checked"];
      interrupt -> execute [lhead=cluster_elt, label="Pause unchecked\n(element restarts)", style=dashed];
      execute -> stop [ltail=cluster_elt, label="Stop"];
   }

.. _sequencer_custom_choice_model:

Writing a custom choice model
-----------------------------

A choice model is a class deriving from ``ChoiceModelBase``
(``pymodaq.extensions.sequencer.utilities.choice_models.model``) and registered with the
``ChoiceModelFactory.register_choice`` decorator. It is a ``ParameterManager``: its ``params`` class attribute
defines the settings displayed in the Choice element editor. The model has access to the Choice element
(``parent_elt``) and to a ``ModulesManager`` holding the Dashboard modules (``modules_manager``).

The ``execute`` method is called when the Choice element is executed. It **must** end by emitting the
``go_to_signal`` of the parent element with a boolean.

Below is an example of a model randomly choosing the True target with a given probability:

.. code-block:: python

    import random
    from typing import Any

    from pymodaq_data import DataToExport
    from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory
    from pymodaq.extensions.sequencer.utilities.choice_models.model import ChoiceModelBase
    from pymodaq.extensions.sequencer.utilities.element_factory import ElementError


    @ChoiceModelFactory.register_choice()
    class RandomChoiceModel(ChoiceModelBase):
        model_name = 'random'  # the name displayed in the Choice element editor

        params = [
            {'title': 'Probability of True:', 'name': 'probability', 'type': 'float',
             'value': 0.5, 'min': 0., 'max': 1.},
        ]

        def execute(self, dte: DataToExport):
            self.parent_elt.go_to_signal.emit(random.random() < self.settings['probability'])

        def check_set_is_valid(self):
            if not 0 <= self.settings['probability'] <= 1:
                raise ElementError(f'Element {self.parent_elt}: the probability should be within [0, 1]')

        def to_dict(self) -> dict[str, Any]:
            return {'probability': self.settings['probability']}

        def from_dict(self, dict_config: dict[str, Any]):
            self.settings['probability'] = dict_config.pop('probability')

The methods you may reimplement are:

* ``execute`` (mandatory): evaluates the condition and emits ``self.parent_elt.go_to_signal`` with ``True`` or
  ``False``
* ``check_set_is_valid``: called before the sequence starts, raise an ``ElementError`` if the settings are not valid
* ``to_dict`` / ``from_dict``: save and restore the model settings in the ``.seq`` files
* ``updated_module_manager``: called when the Dashboard modules change (a new experiment is applied), for instance
  to update a list of detectors in the settings, see the ``threshold`` model

.. note::

  For a model to be "seen" by PyMoDAQ either place it in the ``pymodaq.extensions.sequencer.models`` module or in the
  ``models`` module/folder of a PyMoDAQ plugin declaring the ``pymodaq.models`` entry point.


Writing a custom element
------------------------

An element is a class deriving from ``SeqEltBase`` and registered with both the ``SeqEltFactory.register_elt`` and
``SerializableFactory.register_decorator`` decorators. Below is an example of an element writing a message in the
PyMoDAQ log:

.. code-block:: python

    from typing import Any

    from qtpy import QtWidgets
    from serializall import SerializableFactory

    from pymodaq_data import DataToExport
    from pymodaq_utils.logger import set_logger, get_module_name
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase, SeqEltFactory, ElementError
    from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar

    logger = set_logger(get_module_name(__file__))


    @SerializableFactory.register_decorator()
    @SeqEltFactory.register_elt()
    class MessageElt(SeqEltBase):

        elt_name = 'message'  # unique name, displayed in the Add Element menus
        children_allowed = False  # True for a container element

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.message: str = ''

        def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
            line_edit = QtWidgets.QLineEdit(self.message, parent=base_widget)
            line_edit.textChanged.connect(self.set_message)
            base_widget.add_widget_top(line_edit)
            base_widget.give_focus_to(line_edit)
            return base_widget

        def set_message(self, message: str):
            self.message = message

        def _execute(self, dte: DataToExport = None):
            logger.info(self.message)
            self.done_signal.emit()  # mandatory, otherwise the sequence will hang here

        def check_set_is_valid(self):
            if self.message == '':
                raise ElementError(f'Element {self}: the message is empty')

        def to_dict_custom(self) -> dict[str, Any]:
            return {'message': self.message}

        def from_dict_custom(self, dict_config: dict[str, Any]):
            self.message = dict_config.pop('message')

        def _eq(self, other: 'MessageElt') -> bool:
            return self.message == other.message

        def __repr__(self):
            return f'{super().__repr__()} - {self.message}'

The class attributes and methods to define are:

* ``elt_name``: the unique name of the element
* ``children_allowed``: ``True`` for a container element
* ``_create_widget``: adds the widgets allowing to edit the element on the base widget (a ``WidgetWithToolbar``
  already containing the id, the name and the *Execute* button)
* ``_execute``: performs the action. It **must** eventually emit ``done_signal`` (or ``children_signal`` to execute
  the children of a container, see the ``RepeatElt`` class). Long actions should be asynchronous (signals, callbacks,
  timers) so the GUI is not blocked: the ``done_signal`` is then emitted later, as in the ``WaitElt`` class
* ``check_set_is_valid``: called before the sequence starts, raise an ``ElementError`` if the element is not valid
* ``to_dict_custom`` / ``from_dict_custom``: save and restore the element configuration in the ``.seq`` files
* ``_eq``: tests if two elements have the same configuration

and optionally:

* ``initialize_element``: called each time the element is entered from outside (not when looping over its
  children). Used to reset loop counters
* ``do_things_with_dashboard``: called once the element has access to the Dashboard (``self.dashboard``)
* ``_save_data``: custom processing of the data passed to ``save_data``, which also emits them for logging
* ``size_hint``: the size of the editor popup
* ``__repr__``: the summary displayed in the tree

.. note::

  The elements are registered when their module is imported. The Sequencer automatically imports all the modules of
  the ``pymodaq.extensions.sequencer.utilities.elements`` package. An element defined elsewhere (in a plugin for
  instance) is not discovered automatically: its module has to be imported before the Sequencer is started.
