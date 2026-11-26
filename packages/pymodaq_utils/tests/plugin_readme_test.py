import textwrap

from pymodaq_utils.packages import extract_authors_from_description
from pymodaq_utils.plugin_tools import readme


STANDARD = textwrap.dedent("""
    pymodaq_plugins_demo (Demo)
    ###########################

    .. image:: https://img.shields.io/pypi/v/pymodaq_plugins_demo.svg
       :target: https://pypi.org/project/pymodaq_plugins_demo/

    Some text.

    Authors
    =======

    * First Author  (first@lab.org)
    * Second Author

    .. if needed use this field

        Contributors
        ============

        * Template contributor

    Contributors
    ============

    * Real Contributor

    Instruments
    ===========

    Below is the list of instruments included in this plugin

    Actuators
    +++++++++

    * **Kinesis_KPZ101**: Piezo Electric Stage Kinesis series (KPZ101)
    * **DCServoKCube**: DC Servo motors controlled using a KCube
      (tested with KDC101)

    Viewer0D
    ++++++++

    * **TLPMPowermeter**: TLPM dll compatible series (PM101x, PM100D)

    Viewer1D
    ++++++++

    Viewer2D
    ++++++++

    * **Thorlabs_TSI**: sCMOS camera series Zelux, Kiralux, Quantalux.

    PID Models
    ==========

    Extensions
    ==========

    * **MyExt**: an extension

    Installation instructions
    =========================

    * You need the Kinesis software
    """)


def test_authors_and_contributors():
    info = readme.parse_readme(STANDARD)
    assert info.authors == ['First Author (first@lab.org)', 'Second Author']
    assert info.contributors == ['Real Contributor']  # the one of the comment block is ignored
    assert readme.emails(info.authors[0]) == ['first@lab.org']
    assert extract_authors_from_description(STANDARD) == info.authors


def test_instruments_nested_kinds():
    info = readme.parse_readme(STANDARD)
    assert list(info.instruments) == ['Actuators', 'Viewer0D', 'Viewer2D', 'Extensions']  # empty kinds are dropped
    actuators = info.instruments['Actuators']
    assert [a.name for a in actuators] == ['Kinesis_KPZ101', 'DCServoKCube']
    assert actuators[1].description == 'DC Servo motors controlled using a KCube (tested with KDC101)'  # joined
    assert 'PM100D' in info.instruments['Viewer0D'][0].description
    assert 'You need the Kinesis software' not in str(info.instruments)  # installation section is not read
    assert info.instruments_as_dict()['Actuators'][0] == 'Kinesis_KPZ101: Piezo Electric Stage Kinesis series (KPZ101)'
    assert info.instrument_names() == ['Kinesis_KPZ101', 'DCServoKCube', 'TLPMPowermeter', 'Thorlabs_TSI', 'MyExt']


def test_kinds_at_the_same_level_as_instruments():
    text = textwrap.dedent("""
        Instruments
        ===========

        Actuators
        =========

        * **PEM 200**: controller for the Photoelastic modulator

        .. Viewer0D
        .. ++++++++

        .. * **yyy**: control of yyy 0D detector

        Installation instructions
        =========================

        * Tested with PyMoDAQ 4.4.7
        """)
    assert readme.extract_instruments(text) == {
        'Actuators': [readme.Instrument('PEM 200', 'controller for the Photoelastic modulator')]}


def test_flat_instruments_and_markdown():
    text = textwrap.dedent("""
        # Authors
        * Someone

        ## Instruments
        **KDC101**: Control of the Thorlabs KDC101 motor.

        ### Viewer 2D
        - Camera X: a camera
        - **Camera Y** another one
        """)
    info = readme.parse_readme(text)
    assert info.authors == ['Someone']
    assert info.instruments['Other'] == [readme.Instrument('KDC101', 'Control of the Thorlabs KDC101 motor.')]
    assert info.instruments['Viewer2D'] == [readme.Instrument('Camera X', 'a camera'),
                                            readme.Instrument('Camera Y', 'another one')]


def test_markup_is_removed():
    text = textwrap.dedent("""
        Instruments
        ===========

        Actuators
        +++++++++

        * **Name:** uses ``pylablib`` and `the docs <https://example.org>`_ (see :class:`Foo`)
        """)
    inst = readme.extract_instruments(text)['Actuators'][0]
    assert inst.name == 'Name'
    assert inst.description == 'uses pylablib and the docs (see Foo)'


def test_malformed_input_does_not_raise():
    for text in ('', None, 'no section at all', 'Instruments\n===', '* \n* ', '=====\n=====\n====='):
        info = readme.parse_readme(text)
        assert info.authors == [] and info.instruments == {}


def test_all_readme_kinds_are_normalized():
    for title, kind in (('Actuators', 'Actuators'), ('Actuator', 'Actuators'), ('Viewer0D', 'Viewer0D'),
                        ('viewer 1d', 'Viewer1D'), ('DAQ_Viewer_ND', 'ViewerND'), ('PID models', 'PID Models'),
                        ('Legacy', 'Legacy'), ('Installation', None), ('Infos', None)):
        assert readme._normalize_kind(title) == kind
