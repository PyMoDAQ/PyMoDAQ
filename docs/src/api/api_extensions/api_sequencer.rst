.. _sequencer_api:

The Sequencer Extension
=======================

Summary of the main classes of the :ref:`Sequencer extension <sequencer_extension>`. See also
:ref:`sequencer_developer`.

The Extension
-------------

.. currentmodule:: pymodaq.extensions.sequencer.sequencer

.. autosummary::

   Sequencer
   SequenceWorker

.. autoclass:: Sequencer
   :members:

.. autoclass:: SequenceWorker
   :members:

.. currentmodule:: pymodaq.extensions.sequencer.utilities.sequencer.sequence

.. autoclass:: Sequence
   :members:


Elements
--------

.. currentmodule:: pymodaq.extensions.sequencer.utilities.element_factory

.. autosummary::

   SeqEltBase
   SeqEltFactory
   ElementError

.. autoclass:: SeqEltBase
   :members:

.. autoclass:: SeqEltFactory
   :members:

.. autoclass:: ElementError

The elements shipped with PyMoDAQ:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.state.StateElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.move.MoveElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.grab.GrabElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.wait.WaitElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.repeat.RepeatElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.scanner.ScannerElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.choice.ChoiceElt
   :members:

.. autoclass:: pymodaq.extensions.sequencer.utilities.elements.sequence.SequenceElt
   :members:


Choice models
-------------

.. currentmodule:: pymodaq.extensions.sequencer.utilities.choice_models.model

.. autoclass:: ChoiceModelBase
   :members:

.. autofunction:: get_choice_models

.. currentmodule:: pymodaq.extensions.sequencer.utilities.choice_models.factory

.. autoclass:: ChoiceModelFactory
   :members:

The models shipped with PyMoDAQ:

.. autoclass:: pymodaq.extensions.sequencer.models.threshold_choice_model.ThresholdChoiceModel
   :members:

.. autoclass:: pymodaq.extensions.sequencer.models.user_input_choice.UserInput
   :members:

.. autoclass:: pymodaq.extensions.sequencer.models.true_choice_model.TrueChoiceModel
   :members:

.. autoclass:: pymodaq.extensions.sequencer.models.false_choice_model.FalseChoiceModel
   :members:


State machine
-------------

.. currentmodule:: pymodaq.extensions.sequencer.utilities.states

.. autoclass:: CompositeState
   :members:

.. autoclass:: TrackedTransition
   :members:

.. autoclass:: ValueTransition
   :members:

.. autoclass:: InterruptState
   :members:
