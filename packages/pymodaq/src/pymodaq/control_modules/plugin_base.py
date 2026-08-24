import warnings

from qtpy.QtCore import QObject, Slot
from easydict import EasyDict as edict
from pyqtgraph.parametertree import Parameter
from pyqtgraph.parametertree.parameterTypes import GroupParameter
from pyqtgraph.parametertree.Parameter import registerParameterType

from pymodaq.control_modules.thread_commands import ControllerStatus, ThreadStatus
from pymodaq_gui.parameter import utils as putils
from pymodaq_utils.utils import ThreadCommand

# mapping from pre-5.1 group/parameter names to their current equivalent, kept so that
# plugins written before the 'controller' group renaming (PR #1157/#1173) keep working
_LEGACY_SETTINGS_NAMES = {
    'multiaxes': 'controller',
    'multi_status': 'controller_status',
}

_BACKCOMPAT_SETTINGS_TYPE = 'plugin_backcompat_group'


class _BackCompatGroupParameter(GroupParameter):
    """GroupParameter used only for a plugin's top-level ``settings`` tree.

    Redirects legacy path segments (e.g. ``'multiaxes'``, ``'multi_status'``) to their
    current names so that old plugin code such as ``self.settings['multiaxes', 'axis']``
    keeps working. Registered under its own parameter type name (rather than overriding
    the global ``'group'`` type), so it does not affect every ``GroupParameter`` in the
    application and stays consistent with pyqtgraph's requirement that a Parameter's
    ``type`` option match its registered class.
    """

    def __getitem__(self, names):
        if isinstance(names, str):
            names = (names,)
        try:
            return super().__getitem__(names)
        except KeyError:
            translated = tuple(_LEGACY_SETTINGS_NAMES.get(name, name) for name in names)
            if translated == tuple(names):
                raise
            warnings.warn(
                f"Accessing settings with the legacy name(s) {names} is deprecated and will "
                f"be removed in a future release. Use {translated} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return super().__getitem__(translated)


registerParameterType(_BACKCOMPAT_SETTINGS_TYPE, _BackCompatGroupParameter, override=True)


class PluginBase(QObject):
    """Common base class for DAQ_Move_base and DAQ_Viewer_base.

    Provides the shared __init__ scaffold (settings tree, param restore, parent link),
    emit_status, send_param_status, update_settings, is_master, and
    ini_controller_init (master/slave pattern).

    Subclasses call super().__init__() then add their specific state, and call
    self.ini_attributes() at the appropriate point in their own __init__.
    """

    params = []

    def __init__(self, parent=None, params_state=None):
        QObject.__init__(self)
        self.parent_parameters_path = []
        self.settings = Parameter.create(name='Settings', type=_BACKCOMPAT_SETTINGS_TYPE,
                                         children=self.params)
        if params_state is not None:
            if isinstance(params_state, dict):
                self.settings.restoreState(params_state)
            elif isinstance(params_state, Parameter):
                self.settings.restoreState(params_state.saveState())
        self.settings.sigTreeStateChanged.connect(self.send_param_status)
        self.parent = parent
        self.status = edict(info="", controller=None, initialized=False)
        self.controller = None
        if parent is not None:
            self._title = parent.title
        else:
            self._title = "myplugin"
        # Note: ini_attributes() is NOT called here; each subclass calls it
        # after setting up its own state.

    @property
    def is_master(self) -> bool:
        """True when this plugin is the controller master."""
        return self.settings['controller', 'controller_status'] == ControllerStatus.MASTER

    def ini_attributes(self):
        """Hook called at the end of each subclass __init__ for plugin-specific setup."""
        pass

    def commit_settings(self, param: Parameter):
        """Hook called after every settings change; override to push changes to hardware."""
        pass

    def emit_status(self, status: ThreadCommand):
        """Emit *status* back to the parent worker thread signal, or print if standalone."""
        if self.parent is not None:
            self.parent.status_sig.emit(status)
        else:
            print(status)

    def ini_controller_init(self, old_controller=None, new_controller=None,
                            slave_controller=None):
        """Handle master/slave controller initialization.

        Parameters
        ----------
        old_controller:
            An already-initialized controller coming from a previously initialized plugin
            (Slave case). Deprecated alias: pass via *slave_controller* instead.
        new_controller:
            The freshly created controller instance (Master case).
        slave_controller:
            Preferred keyword for the Slave controller; takes precedence over
            *old_controller* when provided.
        """
        if old_controller is None and slave_controller is not None:
            old_controller = slave_controller
        self.status.update(edict(info="", controller=None, initialized=False))
        if not self.is_master:
            if old_controller is None:
                raise Exception('no controller has been defined externally while this is a slave one')
            controller = old_controller
        else:
            controller = new_controller
        self.controller = controller
        return controller

    def send_param_status(self, param, changes):
        """Forward settings-tree changes to the main GUI via the parent status signal."""
        for param, change, data in changes:
            path = self.settings.childPath(param)
            if change == 'childAdded':
                self.emit_status(ThreadCommand(ThreadStatus.UPDATE_SETTINGS,
                                               [self.parent_parameters_path + path,
                                                [data[0].saveState(), data[1]], change]))
            elif change in ('value', 'limits', 'options'):
                self.emit_status(ThreadCommand(ThreadStatus.UPDATE_SETTINGS,
                                               [self.parent_parameters_path + path, data, change]))
            elif change == 'parent':
                pass

    @Slot(edict)
    def update_settings(self, settings_parameter_dict):
        """Receive a settings change from the GUI and apply it to the local settings tree."""
        try:
            path = settings_parameter_dict['path']
            param = settings_parameter_dict['param']
            change = settings_parameter_dict['change']
            try:
                self.settings.sigTreeStateChanged.disconnect(self.send_param_status)
            except Exception:
                pass
            if change == 'value':
                self.settings.child(*path[1:]).setValue(param.value())
            elif change == 'childAdded':
                child = Parameter.create(name='tmp')
                child.restoreState(param.saveState())
                self.settings.child(*path[1:]).addChild(child)
                param = child
            elif change == 'parent':
                children = putils.get_param_from_name(self.settings, param.name())
                if children is not None:
                    path = putils.get_param_path(children)
                    self.settings.child(*path[1:-1]).removeChild(children)
            self.settings.sigTreeStateChanged.connect(self.send_param_status)
            self.commit_settings(param)
        except Exception as e:
            self.emit_status(ThreadCommand(ThreadStatus.UPDATE_STATUS, str(e)))
