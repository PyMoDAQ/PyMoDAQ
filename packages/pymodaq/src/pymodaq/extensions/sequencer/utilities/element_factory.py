from pathlib import Path
from importlib import import_module
from dataclasses import dataclass, Field, InitVar
from typing import Tuple, Callable, TYPE_CHECKING, Any, Union, Iterable, Mapping

from qtpy import QtCore, QtWidgets


from pymodaq.extensions.sequencer.utilities.states import CompositeState, QState

from qt_themes import get_theme

from serializall import SerializableFactory, SerializableBase

from pymodaq_data import DataToExport
from pymodaq_gui.managers.action_manager import ActionManager, QAction, addaction
from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.qt_utils import mkQApp
from pymodaq_gui.utils.widgets import LabelWithFont
from pymodaq.extensions.sequencer.utilities.widget_with_toolbar import WidgetWithToolbar
from pymodaq_utils.abstract import abstract_attribute
from pymodaq_utils.logger import set_logger, get_module_name
from pymodaq_gui.utils.styling import Font


logger = set_logger(get_module_name(__file__))

if TYPE_CHECKING:
    from pymodaq.dashboard import DashBoard
    from pymodaq.extensions.sequencer.utilities.sequencer.sequence import Sequence

ser_factory = SerializableFactory()

class ElementError(Exception):
    pass


def register_elements(parent_module_name: str = 'pymodaq.extensions.sequencer.utilities'):
    elements = []
    try:
        elements_module = import_module(f'{parent_module_name}.elements')

        element_path = Path(elements_module.__path__[0])

        for file in element_path.iterdir():
            if file.is_file() and 'py' in file.suffix and file.stem != '__init__':
                try:
                    elements.append(import_module(f'.{file.stem}',
                                                  elements_module.__name__))
                except Exception as e:
                    logger.warning(str(e))
    except Exception as e:
        logger.warning(str(e))
    finally:
        return elements


MIME_TYPE = 'pymodaq/sequence_element'


class SeqEltBase(QtCore.QObject, ActionManager):
    """ Base class defining the interface of all elements handled by the Sequencer

    """
    elt_name = abstract_attribute()
    children_signal = QtCore.Signal()
    done_signal = QtCore.Signal()
    save_signal = QtCore.Signal(DataToExport)
    data_to_log_signal = QtCore.Signal(DataToExport)
    go_to_signal = QtCore.Signal(int)

    children_allowed = False
    params = []

    def __repr__(self):
        return f'{self.id} - {self.elt_name.capitalize()}'

    def __init__(self, id: int,
                 parent: 'SeqEltBase'= None,
                 parent_sequence: 'Sequence' = None,
                 **label_kwargs):
        QtCore.QObject.__init__(self)
        ActionManager.__init__(self)

        self._mstate:  CompositeState = None

        self._id = id
        self._dashboard: 'DashBoard' = None
        self._parent_sequence = parent_sequence
        self._parent: 'SeqEltBase' = parent

        self._children = []

        font_name = label_kwargs.pop('font_name', 'Tahoma')
        font_size = label_kwargs.pop('font_size', 10)
        isbold = label_kwargs.pop('isbold', True)
        isitalic = label_kwargs.pop('isitalic', True)

        self.font = Font(font_name, font_size, isbold, isitalic)
        self.save_signal.connect(self.save_data)

    def initialize_element(self):
        """ Perform Initialization of the element if needed when called

        Will be called automatically during the machine execution if the elt it
        comes from (using the StateMachine) is not a child of itself

        To be reimplemented
        """
        pass

    @property
    def mstate(self) -> CompositeState:
        if self._mstate is None:
            self._mstate = CompositeState(self)
        return self._mstate

    def _save_data(self, dte: DataToExport):
        """ to be reimplemented in elements in order to save it's data (if Any)"""
        pass

    def save_data(self, dte: DataToExport):
        self._save_data(dte)
        self.data_to_log_signal.emit(dte)
        self.done_signal.emit()

    @property
    def parent(self) -> 'SeqEltBase':
        """ Get/Set this element parent"""
        return self._parent

    @parent.setter
    def parent(self, value: 'SeqEltBase'):
        self._parent = value

    def set_parent(self, value: 'SeqEltBase'):
        """ to be used as a slot or ..."""
        self.parent = value

    def get_root_elt(self) -> 'SeqEltBase':
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    def get_ids(self, parent_elt: 'SeqEltBase' = None,
                without_ids: Iterable[int] = (),
                without_types: Iterable[type['SeqEltBase']] = ()) -> list[int]:
        """ Get the ids of the existing elements"""
        return [elt.id for elt in self.get_elts(parent_elt, without_ids, without_types)]

    def get_elts(self, parent_elt: 'SeqEltBase' = None,
                 without_ids: Iterable[int] = (),
                 without_types: Iterable[type['SeqEltBase']] = ()) -> list['SeqEltBase']:
        """ Get as a list all element in the tree starting from parent_elt

        Parameters
        ----------
        without_types
        parent_elt: SeqEltBase, Optional (the root element is taken in this case)
        without_ids: tuple[int], optional (default: ())
            tuple of ids to remove from the result
        without_types: tuple[SeqEltBase], optional (default: ())
            tuple of elements type to remove from the result

        Returns
        -------
        list[SeqEltBase]: the retrieved elements
        """
        elts = []
        if parent_elt is None:
            parent_elt = self.get_root_elt()
        for child in parent_elt.children:
            if child.id not in without_ids and type(child) not in without_types:
                elts.append(child)
            elts.extend(self.get_elts(child, without_ids=without_ids,
                                      without_types=without_types))
        return elts

    def get_elts_as_str(self, parent_elt: 'SeqEltBase' = None,
                        without_ids: Iterable[int] = (),
                        without_types: Iterable[type['SeqEltBase']] = ()) -> list[str]:
        """ Get the elements name of all existing elements"""
        return [str(elt) for elt in self.get_elts(parent_elt, without_ids, without_types)]

    def get_elt_from_id(self, elt_id: int,
                        start_parent: 'SeqEltBase' = None,
                        ) -> Union['SeqEltBase', None]:
        """ Get the Element having the specified id  starting from start_parent in the tree

        Parameters
        ----------
        elt_id : int
        start_parent : SeqEltBase
            Optional, if not specified or None, start from the Root of this element hierarchy

        Returns
        -------
        SeqEltBase or None
        """
        if start_parent is None:
            start_parent = self.get_root_elt()
        if start_parent.id == elt_id:
            return start_parent
        elif start_parent.children_allowed:
            for child in start_parent.children:
                target_elt = self.get_elt_from_id(elt_id, child)
                if target_elt is not None:
                    return target_elt
        return None

    @property
    def children(self) -> list['SeqEltBase']:
        return self._children

    @property
    def children_without_add(self) -> list['SeqEltBase']:
        return self._children[:-1]

    def __iter__(self):
        for child in self.children:
            yield child

    def append_child(self, elt: 'SeqEltBase'):
        self.children.append(elt)
        elt.parent = self

    def child(self, index: int) -> Union['SeqEltBase', None]:
        """ Get the child by its index within the list of children"""
        if index < len(self.children):
            return self.children[index]
        return None

    def child_by_index(self, index: int) -> Union['SeqEltBase', None]:
        """ Get the child by its unique index """
        for child in self._children:
            if child.id == index:
                return child
        return None

    @property
    def dashboard(self) -> 'DashBoard':
        return self._dashboard

    @dashboard.setter
    def dashboard(self, value: 'DashBoard'):
        """ """
        self._dashboard = value
        self.do_things_with_dashboard()

    def set_dashboard(self, dashboard: 'DashBoard'):
        self.dashboard = dashboard

    @property
    def parent_sequence(self) -> 'Sequence':
        return self._parent_sequence

    @parent_sequence.setter
    def parent_sequence(self, value: 'Sequence'):
        """ """
        self._parent_sequence = value
        self.do_things_with_parent_sequence()

    def set_parent_sequence(self, parent_sequence: 'Sequence'):
        self.parent_sequence = parent_sequence

    def __eq__(self, other: 'SeqEltBase'):
        if not isinstance(other, self.__class__):
            return False
        for attr in ('id', 'name',):
            if getattr(self, attr) != getattr(other, attr):
                return False
        if self.children_allowed:
            for child, child_other in zip(self.children, other.children):
                if not child.__eq__(child_other):
                    return False
        return self._eq(other)

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value: int):
        self._id = value

    @property
    def name(self):
        return self.elt_name

    @name.setter
    def name(self, value: str):
        self.elt_name = value

    def _create_base_widget(self, parent: QtWidgets.QWidget) -> WidgetWithToolbar:
        """ Base Widget"""


        base_widget = WidgetWithToolbar(parent=parent)
        id_widget = LabelWithFont(f'{self.id}',
                                  font_name=self.font.font_name,
                                  font_size=self.font.font_size,
                                  isbold=self.font.isbold,
                                  isitalic=self.font.isitalic,
                                  color=get_theme().blue,
                                  parent=base_widget)


        name_widget = LabelWithFont(f'{self.name}',
                                    font_name=self.font.font_name,
                                    font_size=self.font.font_size,
                                    isbold=self.font.isbold,
                                    isitalic=self.font.isitalic,
                                    color=get_theme().magenta,
                                    parent=base_widget)
        base_widget.add_widget_top(id_widget)
        base_widget.add_widget_top(name_widget)
        base_widget.add_action('execute', 'Execute', 'start',
                               tip='Execute the Sequencer Element',
                               icon_color=get_theme().magenta,
                               toolbar=base_widget.toolbar)
        base_widget.connect_action('execute', self.execute)
        return base_widget

    @classmethod
    def serialize(cls, obj: 'SeqEltBase') -> bytes:
        """Convert a SeqEltBase object into a bytes string

        Returns
        -------
        bytes: the bytes string
        """
        bytes_string = b''
        bytes_string += ser_factory.get_apply_serializer(obj.to_dict())
        return bytes_string

    @classmethod
    def deserialize(cls, bytes_str: bytes) -> Tuple['SeqEltBase', bytes]:
        """Convert bytes into a SeqEltBase object

        Returns
        -------
        SeqEltBase: the decoded object
        bytes: the remaining bytes string if any
        """
        dict_config, remaining_bytes = ser_factory.get_apply_deserializer(bytes_str, False)
        seq_elt = cls.from_dict(dict_config)

        return seq_elt, remaining_bytes

    def to_dict(self) -> dict[str, Any]:
        """ Serialization in a dictionary"""
        from pymodaq.extensions.sequencer.utilities.elements.button import AddButtonPlaceholder
        dict_config: dict[str, Any] = {'elt_name': self.elt_name,
                                       'id': self.id,}
        dict_config.update(self.to_dict_custom())
        if self.children_allowed:
            dict_config['children'] = []
            for child in self.children:
                if child.elt_name != AddButtonPlaceholder.elt_name:
                    dict_config['children'].append(child.to_dict())
        return dict_config

    @classmethod
    def from_dict(cls, dict_config: dict[str, Any]) -> 'SeqEltBase':
        """ Deserialization from a dictionary

        Returns
        -------
        SeqEltBase: the deserialized object
        """
        elt_name = dict_config.pop('elt_name')
        id = dict_config.pop('id')
        seq_elt = SeqEltFactory().get_seq_elt(elt_name)(id)
        seq_elt.from_dict_custom(dict_config)
        if 'children' in dict_config:
            for child in dict_config['children']:
                seq_elt.append_child(cls.from_dict(child))
            seq_elt.append_child(cls.from_dict({'elt_name': 'button', 'id': -2}))
        return seq_elt

    def create_widget(self, parent: QtWidgets.QWidget = None) -> QtWidgets.QWidget:
        """ Public API to be used to create the widget representing this elt """
        return self._create_widget(self._create_base_widget(parent))

    # list of methods to reimplement in real implementations!

    def _create_widget(self, base_widget: WidgetWithToolbar) -> WidgetWithToolbar:
        """ Particular Widget allowing the edition of this Element

        Parameters
        ----------
        base_widget :
            You should build your widget based on base_widget
        """
        raise NotImplementedError

    def execute(self, dte: DataToExport = None):
        """ Execute the Element

        Should emit the done_signal when executed (could be with empty DataToExport)
        """
        logger.debug(f'Elt {self} executing')
        self._execute(dte)

    def check_set_is_valid(self):
        """ Check the validity of the element

        Will be called before executing the element. Try to make sure the element is valid or return None
        if the user may do something!

        To be reimplemented

        if not valid should raise an ElementError exception else return None"""
        raise NotImplementedError

    def _execute(self, dte: DataToExport = None):
        """ Execute the Element

        Should emit the done_signal when executed (could be with empty DataToExport)
        """
        raise NotImplementedError

    def to_dict_custom(self) -> dict[str, Any]:
        """ adds attribute to a dict in order to produce a human readable
        representation/configuration for this element

        to be reimplemented
        """
        raise NotImplementedError

    def from_dict_custom(self, dict_config: dict[str, Any]):
        """ Create/set the custom part of the element to finish initialization
        using setters, attribute assignment or methods

        to be reimplemented
        """
        raise NotImplementedError

    def _eq(self, other: 'SeqEltBase'):
        """ Custom method to reimplement to assert two elements are equals"""
        raise NotImplementedError

    def do_things_with_dashboard(self):
        """ If this Element is using the Dashboard, once its setter has been called, this method will be executed

        Do whatever is needed to instantiate your element with the Dashboard
        """
        pass

    def do_things_with_parent_sequence(self):
        """ If this Element is using the Dashboard, once its setter has been called, this method will be executed

        Do whatever is needed to instantiate your element with the Dashboard
        """
        pass

    def size_hint(self) -> QtCore.QSize:
        """Returns the Size the corresponding widget will likely have"""
        return QtCore.QSize(200, 50)


class SeqEltFactory:
    """The factory class to get Sequencer Elements"""

    elements_registry = {}

    @classmethod
    def register_elt(cls) -> Callable:
        """Class decorator method to register SubEntryHandlers class to the internal
        registry.
        Must be used as a decorator above the definition of an SubEntryHandler inherited class.

        The entry class must implement specific class attributes and methods
        """

        def inner_wrapper(wrapped_class: type[SeqEltBase]) -> type[SeqEltBase]:
            elt_name = wrapped_class.elt_name

            if elt_name not in cls.elements_registry:
                cls.elements_registry[elt_name] = wrapped_class
            else:
                logger.info(f"Subentry {elt_name} already registered")
            # Return wrapped_class
            return wrapped_class

        # Return decorated function
        return inner_wrapper

    @classmethod
    def get_seq_elt(cls, name: str) -> type[SeqEltBase]:
        """Factory command to get registered subentry handler.

        This method gets the appropriate executor class from the registry
        """

        if name not in cls.elements_registry:
            raise KeyError(f"{name} is not a supported element.")

        return cls.elements_registry[name]

    @property
    def elements(self) -> list[str]:
        return [elt for elt in self.elements_registry.keys()]


