from serializall import SerializableFactory

from pymodaq.extensions.sequencer.utilities.element_factory import SeqEltFactory
from pymodaq.extensions.sequencer.utilities.elements.group import GroupElt


@SerializableFactory.register_decorator()
@SeqEltFactory.register_elt()
class RootElt(GroupElt):
    """ The sequence's singular, auto-created top-level container.

    A GroupElt in every respect (runs its children once, then finishes) except for its
    special id=-1 default - unlike GroupElt itself, RootElt is never user-added via the tree's
    "Add Element" menu (explicitly excluded there), only ever created once per Sequence as
    its implicit root.
    """
    elt_name = 'root'

    def __init__(self, id: int = -1, parent=None, **kwargs):  # should keep the signature of the base
        # Pass a specific string or ID to distinguish it from standard data
        super().__init__(id=id, parent=parent, **kwargs)
