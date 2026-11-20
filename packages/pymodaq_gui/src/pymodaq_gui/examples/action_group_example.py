"""
Action groups example: several actions under a single toolbar button

Demonstrates ActionManager.add_action_group and the ActionGroup it creates:

- a group with a checkable *primary* action (the button face) and checkable entries in its dropdown, and an
  Indicator telling, by the colour of its icon, that the hidden entries change something (Transform)
- an *exclusive* group without primary: a radio choice, the button shows the icon of the checked entry (X axis)
- *dynamic* entries replaced at runtime, keeping the state the user set by key (Channels)
- a *nested* group, displayed as a submenu of another group (View > Grid)

Every change of an entry is reported through the ``entry_toggled`` signal of its group, shown in the log.
Checkable entries do not close the dropdown, so several can be toggled in a row.
"""
import sys

from qtpy import QtWidgets

from pymodaq_gui.managers.action_manager import ActionManager, Indicator


class ActionGroupExample(QtWidgets.QMainWindow, ActionManager):

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        ActionManager.__init__(self, toolbar=self.addToolBar('groups'))
        self.setWindowTitle('Action groups example')
        self.resize(700, 450)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        self.setCentralWidget(central)
        self.channels_spinbox = QtWidgets.QSpinBox()
        self.channels_spinbox.setRange(0, 6)
        self.channels_spinbox.setValue(3)
        self.channels_spinbox.setPrefix('Number of channels: ')
        layout.addWidget(self.channels_spinbox)
        self.log = QtWidgets.QTextEdit(readOnly=True)
        layout.addWidget(self.log)

        self.setup_actions()
        self.connect_things()
        self.update_channels(self.channels_spinbox.value())

    def setup_actions(self):
        # 1. Primary + checkable entries: the primary is a master switch, the entries say what it applies
        self.add_action_group(
            'transform', 'Transform', 'flip', tip='Apply the transforms checked in the dropdown', checkable=True,
            secondary_actions=[
                dict(short_name='flip_ud', name='Flip up/down', icon_name='flip', rotate=90, checkable=True),
                dict(short_name='flip_lr', name='Flip left/right', icon_name='flip', checkable=True),
                dict(short_name='rotate', name='Rotate', icon_name='rotate_90_degrees_cw', checkable=True),
            ])

        # 2. Exclusive, no primary: clicking the button opens the choice
        self.add_action_group(
            'x_axis', 'X axis', 'function', tip='What the x axis shows', primary=False, exclusive=True,
            secondary_actions=[
                dict(short_name='x_samples', name='Samples', icon_name='format_list_numbered',
                     checkable=True, checked=True),
                dict(short_name='x_timestamps', name='Timestamps', icon_name='timer', checkable=True),
                dict(short_name='x_xy', name='XY (channel 0 as x)', icon_name='scatter_plot', checkable=True),
            ])

        # 3. Entries set at runtime (see update_channels), primary: show the legend
        self.add_action_group('channels', 'Legend', 'layers', tip='Show the legend', checkable=True, checked=True)

        # 4. Nested group: View has no primary, its 'grid' group is a submenu whose first entry is its primary
        self.add_action_group(
            'view', 'View', 'visibility', tip='View options', primary=False,
            secondary_actions=[
                dict(short_name='aspect_ratio', name='Lock aspect ratio', icon_name='aspect_ratio', checkable=True),
                dict(group='grid', name='Grid', icon_name='grid_on', checkable=True,
                     secondary_actions=[
                         dict(short_name='minor_ticks', name='Minor ticks', icon_name='line_style', checkable=True),
                     ]),
            ])

    def connect_things(self):
        self.channels_spinbox.valueChanged.connect(self.update_channels)
        for name in ('transform', 'x_axis', 'channels', 'view', 'grid'):
            self.get_action_group(name).entry_toggled.connect(
                lambda key, checked, name=name: self.log.append(f'{name}: {key} -> {checked}'))
        # the primary actions are regular actions
        self.connect_action('transform', lambda checked: self.log.append(f'transform (primary) -> {checked}'))
        self.connect_action('channels', lambda checked: self.log.append(f'legend (primary) -> {checked}'))

        self.connect_action('transform', self.update_transform_indicator)
        self.get_action_group('transform').entry_toggled.connect(self.update_transform_indicator)
        self.get_action_group('channels').entry_toggled.connect(self.update_channels_indicator)

    def update_channels(self, number: int):
        """Replace the channel entries: a channel hidden by the user stays hidden, keyed by its label"""
        self.set_action_group_entries('channels', [
            dict(short_name=f'channel_{index}', key=f'Ch{index}', name=f'Ch{index}', checkable=True, checked=True)
            for index in range(number)])
        self.update_channels_indicator()

    def update_transform_indicator(self, *args):
        group = self.get_action_group('transform')
        applied = [group.get_entry(key).text() for key in group.keys() if group.is_checked(key)]
        if self.is_action_checked('transform') and applied:
            self.set_action_group_indicator('transform', Indicator.ACTIVE, f'Applied: {", ".join(applied)}')
        else:
            self.set_action_group_indicator('transform', Indicator.DEFAULT)

    def update_channels_indicator(self, *args):
        group = self.get_action_group('channels')
        hidden = [key for key in group.keys() if not group.is_checked(key)]
        if len(group.keys()) > 0 and len(hidden) == len(group.keys()):
            self.set_action_group_indicator('channels', Indicator.EMPTY, 'No channel shown')
        elif hidden:
            self.set_action_group_indicator('channels', Indicator.PARTIAL, f'Hidden: {", ".join(hidden)}')
        else:
            self.set_action_group_indicator('channels', Indicator.DEFAULT)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = ActionGroupExample()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
