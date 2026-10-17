from typing import Callable, Optional, TYPE_CHECKING

from pymodaq.utils.managers.modules_manager import ModulesManager
from pymodaq_utils.logger import set_logger, get_module_name

if TYPE_CHECKING:
    from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltBase

logger = set_logger(get_module_name(__file__))


class ModulesManagerBinding:
    """ Owns a ModulesManager kept in sync with the Dashboard's detector/actuator catalog.

    Plain composition, not a mixin: an element that needs live detector/actuator info
    (GrabElt; a condition model that probes detectors) constructs one explicitly -
    `self.modules = ModulesManagerBinding(self)` - rather than inheriting the behavior.
    Elements that don't need it (WaitElt, RepeatElt...) simply never create one; there's
    nothing to opt out of.

    `on_refresh` is the one optional extra: most owners only need the raw catalog kept current
    (`self.modules_manager.detectors_all`/`.actuators_all`), but some also need to react every
    time it refreshes (GrabElt re-filters its own selection; a condition holder also tells its
    current model `updated_module_manager()`) - pass a callable for that, or leave it out.
    """

    def __init__(self, elt: 'SeqEltBase', on_refresh: Optional[Callable[[], None]] = None):
        self.elt = elt
        self.modules_manager = ModulesManager()
        self.on_refresh = on_refresh

    def bind(self):
        """ Call from the owning element's do_things_with_dashboard """
        self.elt.dashboard.experiment_manager.applied_entry.connect(self.refresh)
        self.refresh()

    def refresh(self):
        self.modules_manager.detectors_all = self.elt.dashboard.modules_manager.detectors_all
        self.modules_manager.actuators_all = self.elt.dashboard.modules_manager.actuators_all
        if self.on_refresh is not None:
            self.on_refresh()

    @staticmethod
    def filter_selected(selected: list[str], available: list[str]) -> list[str]:
        """ Keep only the names in `selected` still present in `available`, preserving order.

        The "preserve the user's choice across a catalog refresh" half of reacting to
        on_refresh - every owner that tracks a detector/actuator selection (GrabElt,
        ThresholdChoiceModel, BandsSwitchModel) needs exactly this. Hand-rolling it per owner
        is what let one of them silently regress to "force-select everything" instead.
        """
        for name in selected:
            if name not in available:
                logger.warning(f'{name} is no longer available, dropping it from the selection')
        return [name for name in selected if name in available]
