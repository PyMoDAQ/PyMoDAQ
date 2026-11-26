from pymodaq_gui.utils.status_palette import Status, StatusPalette

from pymodaq_ontology.channel_tree import ChannelRow, ChannelTree


def test_rows_are_grouped_then_by_module(qtbot):
    tree = ChannelTree()
    qtbot.addWidget(tree)
    tree.set_rows([
        ChannelRow('Magnet', 'actuator', 'Magnet', 'Actuators', term_label='Field', status='assigned'),
        ChannelRow('Det/d/A', 'detector', 'd/A', 'Detectors', module='Det'),
        ChannelRow('Det/d/B', 'detector', 'd/B', 'Detectors', module='Det'),
    ])

    assert [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] == ['Actuators', 'Detectors']
    magnet = tree.topLevelItem(0).child(0)  # an actuator has no level for its module
    assert (tree.key_of(magnet), tree.kind_of(magnet), magnet.text(1)) == ('Magnet', 'actuator', 'Field')
    detector_group = tree.topLevelItem(1).child(0)
    assert detector_group.text(0) == 'Det' and detector_group.childCount() == 2
    assert tree.key_of(detector_group) is None  # a group is not a channel
    assert tree.kind_of(detector_group.child(0)) == 'detector'


def test_led_colour_comes_from_the_status_palette(qtbot):
    tree = ChannelTree()
    qtbot.addWidget(tree)
    tree.set_rows([ChannelRow('a', 'actuator', 'a', 'Actuators', status='assigned'),
                   ChannelRow('b', 'actuator', 'b', 'Actuators', status='missing')])

    colours = [tree.topLevelItem(0).child(i).foreground(3).color() for i in range(2)]
    assert colours == [StatusPalette.color(Status.IDLE), StatusPalette.color(Status.ERROR)]
