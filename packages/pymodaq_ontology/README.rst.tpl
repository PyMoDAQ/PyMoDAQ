PyMoDAQ Ontology
################

Assign the terms of an ontology to the channels of the instruments (control modules) loaded in the PyMoDAQ Dashboard.

Install it in the environment of PyMoDAQ: the Dashboard then adds an *Ontology* manager to its *Tools* menu (see the
``pymodaq.managers`` entry point group). The manager

* reads the terms of an ontology from a *source*: a ``terms`` TOML file or an ``rdf`` file (Turtle, RDF/XML, JSON-LD,
  read with rdflib, the ``subClassOf`` relations give the tree of terms); plugins can register other source types in
  the ``pymodaq.ontology_sources`` entry point group,
* lists the channels of the actuators and of the detectors (a probe action does a snap of the detectors to find the
  channels they emit),
* lets you assign a term to each channel (double click on the term of a channel), and keeps the assignment in an entry
  file for each experiment.
