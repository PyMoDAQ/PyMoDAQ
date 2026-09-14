from pymodaq.extensions.sequencer.sequencer import Sequencer


def main():
    import sys
    from pymodaq_gui.qt_utils import mkQApp
    from pymodaq.dashboard import load_dashboard_with_arguments
    from pymodaq.utils.gui_utils.loader_utils import create_extension

    app = mkQApp('Custom Ext')

    win, dashboard, ext = load_dashboard_with_arguments(show_dashboard=False,
                                                        load_extension=False,
                                                        )
    win.mainwindow.setVisible(False)

    win_ext, ext = create_extension(dashboard, Sequencer)
    win_ext.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()