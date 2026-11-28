.. _ontology_manager:

Ontology manager
================

The package ``pymodaq_ontology`` adds an *Ontology* manager to the Dashboard (see :ref:`custom_app`, and
"Adding a manager to the Dashboard" in :ref:`extension_plugins`). It answers one question: **what does each channel of my
instruments mean?** The user picks, for each channel, a term of an ontology, and the choice is kept for the experiment and
written in the saved data. This page is a map of the package: what the objects are, who talks to whom, and where to add
things.

.. contents::
    :local:
    :depth: 2

What is an ontology, and what is it for?
----------------------------------------

Instruments name their data as their authors thought of it: ``Det_1/Spectrum/CH00``, ``M2``, ``Ch1``. Two setups doing the
same experiment give different names, and a file read years later says what was measured only to those who were there.

An **ontology** is a shared vocabulary: a list of concepts (*Spectrum*, *Transmittance*, *BeamBlock*...), each with an
identifier (an IRI, a web-style name that is unique and does not change), a definition, and relations to the other
concepts. The relation used here is *is a kind of*: a *SampleSpectrum* is a *Spectrum*, which is a *Signal*. Ontologies
already exist for many fields (units, quantities, observations, materials...), and a lab can write a small one for its
own experiment.

Assigning a term to a channel says **what the channel is, not what it is called**. This gives:

* **files that explain themselves**: the IRI is saved next to the array, so a program (or a person) finds the spectra of
  a file whatever the instruments were named;
* **the same code on different setups**: an extension asks for "the channels that are a Spectrum" instead of
  hard-coding ``Det_1``;
* **questions that follow the relations**: asking for *Spectrum* also returns the channels assigned a *SampleSpectrum* or
  a *DarkSpectrum*, because they are kinds of it;
* **exchange with other tools and databases** that use the same identifiers.

PyMoDAQ does not interpret the ontology: it reads the list of terms and their *is a kind of* relations, lets the user
assign them, and records the choice. What the terms imply (formulas, units, protocols) is left to the extensions that
use them.

Vocabulary
----------

.. list-table::
    :header-rows: 1
    :widths: 18 82

    * - Word
      - Meaning
    * - ontology
      - A file (or any place) describing concepts and how they relate: *a Spectrum is a Signal*. PyMoDAQ does not
        interpret it, it only reads the terms.
    * - source
      - The code that reads an ontology from somewhere in some format and returns its terms
        (``OntologySource``). ``rdf`` reads an RDF file with rdflib.
    * - term
      - What the manager knows of one concept (``OntologyTerm``): an IRI (its identifier), a label to show, a
        description, the kinds of channel it is meant for (*roles*) and its parents (*broader*). It is a small copy,
        independent from the ontology library.
    * - channel
      - What a term is assigned to (``Channel``): one array of the data of a detector, or one actuator.
    * - assignment
      - The table *channel key -> IRI of a term* (``Assignment``).
    * - entry
      - The file where the manager keeps the source and the assignment of an experiment (``.ontology``, TOML).

The window
----------

.. image:: /image/ontology_manager/ontology_manager.png
    :alt: The Ontology manager with a spectrometer experiment
    :width: 90%

The manager during an assignment (the spectrometer example of the mockexamples plugin). The row at the top is the
source of the terms (type, location, *Load*). The tree lists the channels: the actuators, then the detectors grouped by
module, each with its term, its last value (the last position of an actuator, or the unit of a detector channel, until
a probe finds a value) and a status led (see `Status of a channel`_). The toolbar updates the channels from the
Dashboard, shows the recap table and probes the detectors. A double click on the term of a channel opens the popup of
terms:

.. image:: /image/ontology_manager/ontology_term_picker.png
    :alt: The popup to choose the term of a channel
    :width: 55%

The popup searches the labels, shows the terms as the tree of their *is a kind of* relations, and describes the selected
term below with its IRI. Only the terms that fit the kind of channel (a detector here) are listed; the box *Show all
terms* adds the others.

The pieces
----------

The package has one orchestrator, ``OntologyManager``, and small objects around it that do one thing each. Three
diagrams follow it through its three jobs. In all of them, blue boxes are the user interface, orange boxes are plain
Python (no Qt) and grey boxes belong to something else.

1. Reading the ontology
~~~~~~~~~~~~~~~~~~~~~~~

.. graphviz::
   :caption: The manager asks the factory for a source, the source returns the terms

   digraph reading {
     rankdir=LR; nodesep=0.4; ranksep=0.6; node [shape=box, fontname="Helvetica", fontsize=10, style=filled];
     edge [fontname="Helvetica", fontsize=9];
     mgr [label="OntologyManager\nset_source()", fillcolor="#b5d3ee"];
     factory [label="SourceFactory\ncreate('rdf', location)", fillcolor="#fbe5cc"];
     src [label="RdfSource\nterms()", fillcolor="#fbe5cc"];
     file [label="ontology file\n.ttl, .rdf, .jsonld", shape=note, fillcolor="#eeeeee"];
     term [label="list of OntologyTerm\n(IRI, label, roles, broader)", fillcolor="#fbe5cc"];
     hier [label="TermHierarchy\nis_a, descendants...", fillcolor="#fbe5cc"];
     mgr -> factory [label="1. type and location"];
     factory -> src [label="2. builds"];
     src -> file [label="3. reads"];
     src -> term [label="4. returns"];
     term -> mgr [label="5. kept by the manager"];
     term -> hier [label="built from"];
   }

2. Assigning a term to a channel
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graphviz::
   :caption: From the instruments of the Dashboard to the entry file

   digraph assigning {
     rankdir=LR; nodesep=0.4; ranksep=0.6; node [shape=box, fontname="Helvetica", fontsize=10, style=filled];
     edge [fontname="Helvetica", fontsize=9];
     dash [label="Dashboard\nactuators, probe\nof the detectors", fillcolor="#eeeeee"];
     chan [label="Channel list\n(channels.py)", fillcolor="#fbe5cc"];
     mgr [label="OntologyManager", fillcolor="#b5d3ee"];
     tree [label="ChannelTree\nchannels, terms, leds", fillcolor="#dbe9f6"];
     picker [label="TermPicker\npopup", fillcolor="#dbe9f6"];
     assign [label="Assignment\n{channel key: IRI}", fillcolor="#fbe5cc"];
     entry [label="entry file\n(.ontology, TOML)", shape=note, fillcolor="#eeeeee"];
     dash -> chan [label="1. channels"];
     chan -> mgr;
     mgr -> tree [label="2. rows to show"];
     tree -> mgr [label="3. double click"];
     mgr -> picker [label="4. opens"];
     picker -> mgr [label="5. chosen IRI"];
     mgr -> assign [label="6. assign()"];
     assign -> entry [label="7. saved at once"];
   }

3. Writing the terms in the saved data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. graphviz::
   :caption: The data preparer added to the worker of an extension

   digraph saving {
     rankdir=LR; nodesep=0.4; ranksep=0.6; node [shape=box, fontname="Helvetica", fontsize=10, style=filled];
     edge [fontname="Helvetica", fontsize=9];
     ext [label="extension\n(for instance DAQ_Scan)", fillcolor="#eeeeee"];
     mgr [label="OntologyManager\nattach_worker(worker)", fillcolor="#b5d3ee"];
     worker [label="worker of the extension\nadd_data_preparer", fillcolor="#eeeeee"];
     prep [label="preparer\nannotate_bundle()", fillcolor="#fbe5cc"];
     assign [label="Assignment", fillcolor="#fbe5cc"];
     h5 [label="saved file\narrays with semantic_iri", shape=note, fillcolor="#e2f0d9"];
     ext -> mgr [label="1. asks"];
     mgr -> worker [label="2. adds the preparer"];
     worker -> prep [label="3. each bundle to save"];
     prep -> assign [label="4. reads the IRIs"];
     prep -> worker [label="5. adds semantic_iri"];
     worker -> h5 [label="6. writes"];
   }

The orange boxes (``terms``, ``sources``, ``channels``, ``assignment``, ``annotation``) have no Qt and no PyMoDAQ GUI
dependency: they can be tested without a Dashboard.

Classes and their parents
-------------------------

.. graphviz::
   :caption: Inheritance (an arrow goes from the class to its parent)

   digraph inheritance {
     rankdir=BT; node [shape=box, fontname="Helvetica", fontsize=10, style=filled, fillcolor="#dbe9f6"];
     OntologyManager -> ManagerBase; OntologyManager -> DashboardMixin;
     ManagerBase -> CustomApp;
     ChannelTree -> QTreeWidget; TermPicker -> QDialog;
     RdfSource -> OntologySource; OntologySource -> ABC;
     YourSource [label="YourSource\n(in a plugin)", fillcolor="#fbe5cc", style="filled,dashed"];
     YourSource -> OntologySource [style=dashed];
     OntologyTerm [fillcolor="#fbe5cc"]; Channel [fillcolor="#fbe5cc"]; ChannelRow [fillcolor="#fbe5cc"];
     OntologyTerm -> dataclass [style=dotted, arrowhead=none]; Channel -> dataclass [style=dotted, arrowhead=none];
     ChannelRow -> dataclass [style=dotted, arrowhead=none]; dataclass [shape=plaintext, fillcolor=white, style=solid];
   }

.. list-table::
    :header-rows: 1
    :widths: 22 22 56

    * - Class
      - Parent
      - Role
    * - ``OntologyManager``
      - ``DashboardMixin``, ``ManagerBase``
      - The orchestrator. ``ManagerBase`` gives the entries (one file per experiment, the *Tools* menu, the toolbar) and
        the settings of the window; ``DashboardMixin`` gives ``self.dashboard`` and the call to
        ``do_things_after_experiment_set`` when an experiment is applied. It has ``own_modules_manager = False``: it
        only looks the modules of the Dashboard up.
    * - ``OntologySource``
      - ``ABC``
      - Contract of a source: ``source_type`` (the name used in entry files) and ``terms()``.
    * - ``RdfSource``
      - ``OntologySource``
      - ``source_type = 'rdf'``: an RDF file read with rdflib.
    * - ``SourceFactory``
      -
      - Registry of the source types: ``register`` (class decorator), ``create(type, location)``,
        ``from_identifier('rdf:/path/file.ttl')``. It also loads the types declared in the ``pymodaq.ontology_sources``
        entry point group.
    * - ``OntologyTerm``
      - frozen dataclass
      - One term. ``fits(kind)`` tells whether it can describe a detector or an actuator channel.
    * - ``TermHierarchy``
      -
      - The *is a kind of* relation between terms, built from ``broader``: ``parents``, ``children``, ``ancestors``,
        ``descendants``, ``is_a``.
    * - ``Channel``
      - frozen dataclass
      - A channel and its ``key``: ``module/data name/label`` for a detector array, ``module`` for an actuator.
    * - ``Assignment``
      -
      - ``{channel key: IRI}`` with ``get`` and ``set`` (an empty IRI removes the assignment).
    * - ``ChannelTree``
      - ``QTreeWidget``
      - Shows the channels grouped (*Actuators* / *Detectors*, then by module) with term, last value and a status led.
        It knows nothing of terms: it receives ``ChannelRow`` objects.
    * - ``TermPicker``
      - ``QDialog``
      - The popup opened by a double click: search field, tree of terms (only the compatible ones, a box to show all),
        and the description of the selected term.

From a term of the ontology to a saved array
--------------------------------------------

.. graphviz::
   :caption: Life of an assignment

   digraph flow {
     rankdir=TB; node [shape=box, style=filled, fillcolor="#dbe9f6", fontname="Helvetica", fontsize=10];
     a [label="1. The user chooses a source\n('rdf', path of a .ttl) and presses Load"];
     b [label="2. RdfSource.terms() reads the file\nand returns the OntologyTerm list"];
     c [label="3. Update channels / Probe detectors\nChannel list (actuators: one each,\ndetectors: snap, one per array)"];
     d [label="4. Double click on the term of a channel\nTermPicker -> IRI"];
     e [label="5. manager.assign(key, iri)\nAssignment.set + save the entry file\n(<config>/ontology/<experiment>/*.ontology)"];
     f [label="6. An extension calls manager.attach_worker(worker)\nthe annotation preparer is added to the worker", fillcolor="#fbe5cc"];
     g [label="7. At each bundle to save, the preparer reads the assignment\nand, for the first bundle only, adds the extra attribute\nsemantic_iri to the data (one IRI, or one per array)", fillcolor="#fbe5cc"];
     h [label="8. The file written has the IRI next to the array\nit describes", fillcolor="#e2f0d9"];
     a -> b -> c -> d -> e -> f -> g -> h;
     e -> e [label="each change is saved at once", fontsize=9];
   }

1. **Source.** The location is typed or browsed in the manager, the type comes from ``SourceFactory.names()``.
   ``set_source`` reads the terms; if that fails, the previous terms are kept and the reason is shown in the status line.
2. **Terms.** From an RDF file, a term is (see ``sources/rdf.py``):

   .. list-table::
       :header-rows: 1
       :widths: 35 65

       * - In the RDF graph
         - In the ``OntologyTerm``
       * - ``owl:Class`` or ``owl:NamedIndividual`` with an ``rdfs:label``
         - one term (no label: it is structure of the ontology, not a term); ``category`` is *Classes* or *Individuals*
       * - ``rdfs:label`` (English first)
         - ``label``
       * - ``skos:definition``, else ``rdfs:comment``
         - ``description``
       * - ``rdfs:subClassOf`` (a class), ``rdf:type`` (an individual)
         - ``broader`` (the parents)
       * - the class is a kind of ``sosa:ObservableProperty`` / ``sosa:ActuatableProperty``
         - ``roles`` = ``('detector',)`` / ``('actuator',)``; the roles are inherited through ``subClassOf``

   A term without roles fits any channel. Assigning a term that does not fit is allowed: the led turns orange and the
   recap says so.
3. **Channels.** The actuators are known from the Dashboard at once. The channels of the detectors are only known once
   they emitted data: *Probe detectors* does a snap with a modules manager of its own (the selection of the Dashboard is
   not changed). Channels found by a previous probe are kept when the actuators are updated.
4. **Assignment and entry.** The entry file is TOML:

   .. code-block:: toml

       [source]
       type = "rdf"
       location = "/path/to/spectro_ontology.ttl"

       [assignments]
       "Spectro/Spectrum/CH00" = "http://example.org/mockexamples#SampleSpectrum"
       "BeamBlock" = "http://example.org/mockexamples#BeamBlock"

   The key of a detector channel is ``module/data name/label``, the one of an actuator is the name of its module. An
   assigned channel that the Dashboard no longer has stays in the file and is shown under *Not in the Dashboard* with a
   red led. When the experiment is applied, the manager reads the entry of the experiment and reloads its source.
5. **Annotation.** ``attach_worker`` is meant to be called by an extension, for the worker that saves its data (anything
   with ``add_data_preparer`` / ``remove_data_preparer``); ``quit_fun`` detaches all the workers. The manager does not
   know the extensions. The attribute ``semantic_iri`` is added only to the first bundle of an acquisition (``save_index
   == 0``), the attributes being written when the arrays are created. Its value is one IRI if all the arrays of the data
   have the same term, else a list with one IRI per array (empty text for an array without a term).

Asking what a channel means
---------------------------

Channels are named by the instruments (``Det_1/Spectrum/CH00``), the terms say what they are. ``TermHierarchy`` and
``OntologyManager.channels_of_concept`` ask the second question:

.. code-block:: python

    # every channel whose term is a Spectrum or a kind of Spectrum (SampleSpectrum, DarkSpectrum...)
    channels = manager.channels_of_concept('http://example.org/mockexamples#Spectrum')

    manager.hierarchy.is_a(sample_iri, spectrum_iri)   # True: a SampleSpectrum is a Spectrum
    manager.hierarchy.descendants(spectrum_iri)        # all the kinds of Spectrum, the closest first

The hierarchy is rebuilt from the terms each time it is asked for; parents that the ontology does not know and loops
are ignored. There is no query language: the question is *is this term the concept or below it?*

Status of a channel
-------------------

.. list-table::
    :header-rows: 1
    :widths: 15 15 70

    * - Status
      - Led
      - Meaning
    * - ``none``
      - grey
      - No term assigned.
    * - ``assigned``
      - green
      - A term is assigned and fits the kind of channel (or its roles are not known).
    * - ``incompatible``
      - orange
      - The term is meant for the other kind of channel (for instance a detector term on an actuator).
    * - ``missing``
      - red
      - The assignment names a channel that is not in the Dashboard.

Where to add things
-------------------

**A new source type** (a database, a web address, another format): subclass ``OntologySource``, define ``source_type``
and ``terms()``, and register it. In the package, add a module to ``sources/`` using the decorator; from a plugin,
declare the class in the entry point group:

.. code-block:: python

    from pymodaq_ontology.source_factory import OntologySource, SourceFactory
    from pymodaq_ontology.terms import OntologyTerm

    @SourceFactory.register
    class CsvSource(OntologySource):
        source_type = 'csv'

        def terms(self) -> list[OntologyTerm]:
            ...  # read self.location, raise if it cannot be read

.. code-block:: toml

    [project.entry-points."pymodaq.ontology_sources"]
    csv = "my_plugin.ontology:CsvSource"

The identifier of the source in the entry files is then ``csv:<location>``.

**Annotating the data of an extension**: get the manager from the Dashboard and call ``attach_worker(worker)`` before the
acquisition (and ``detach_worker`` after, if the extension stays open).

**Another way to show or pick terms**: ``ChannelTree`` and ``TermPicker`` only exchange plain objects (``ChannelRow``,
``OntologyTerm``, IRIs) with the manager, so they can be replaced without touching the data part.
