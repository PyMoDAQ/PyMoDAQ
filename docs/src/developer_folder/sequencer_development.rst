.. _sequencer_developer:

Extending the Sequencer
=======================

This page describes how the :ref:`Sequencer extension <sequencer_extension>` works under the hood, and how to write
your own choice models and elements. The classes involved are described in the API section, see :ref:`sequencer_api`.

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

Each element is serialized in the ``.seq`` files using its ``to_dict`` method: the ``elt_name`` and ``id`` common
fields, completed by the element specific fields returned by its ``to_dict_custom`` method (see
:ref:`sequencer_seq_files`). The ``SeqEltFactory`` is then used to recreate the element from its ``elt_name`` when
loading a file.

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
* ``to_dict`` / ``from_dict``: save and restore the model settings in the ``.seq`` files. The returned keys are added
  to the fields of the Choice element
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

* ``elt_name``: the unique name of the element, also used as the ``elt_name`` field in the ``.seq`` files
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
