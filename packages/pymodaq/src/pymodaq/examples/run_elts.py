from pymodaq.extensions.sequencer.utilities.elements.choice import ChoiceElt
from qtpy import QtWidgets

from pymodaq.dashboard import create_load_dashboard
from pymodaq_data import DataToExport
from pymodaq_gui.utils.utils import mkQApp

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory, SeqEltBase
from pymodaq.extensions.sequencer.utilities.elements.grab import GrabElt
from pymodaq.extensions.sequencer.utilities.choice_models.factory import ChoiceModelFactory

choice_factory = ChoiceModelFactory()


if __name__ == "__main__":
    seq_fact = SeqEltFactory()

    app = mkQApp('Elements')

    shared_ui, dashboard = create_load_dashboard()

    def print_dte(dte: DataToExport):
        print(dte)

    widgets: list[QtWidgets.QWidget] = []
    elements: list[SeqEltBase] = []
    for ind_elt, elt_name in enumerate(seq_fact.elements):
        if not (elt_name == 'button' or elt_name == 'root'):
            try:
                if elt_name == 'choice':
                    elts = []
                    for choice_model in choice_factory.models:
                        elt: ChoiceElt = seq_fact.get_seq_elt(elt_name)(ind_elt)
                        elt.choice_model = choice_model
                        elts.append(elt)
                else:
                    elt: SeqEltBase = seq_fact.get_seq_elt(elt_name)(ind_elt)
                    elts = [elt]
                for elt in elts:
                    if elt_name == 'grab':
                        elt.modules_manager.settings['detectors'] = dict(all_items=['yui', 'opoiu'],
                                                                        selected=[])
                    elements.append(elt)
                    widgets.append(elements[-1].create_widget())
                    widgets[-1].show()
                    elements[-1].done_signal.connect(print_dte)
                    print(widgets[-1].sizeHint())
            except Exception as e:
                print(e)
    shared_ui.show()

    app.exec()