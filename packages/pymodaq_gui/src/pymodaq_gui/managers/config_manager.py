from pathlib import Path

from qtpy import QtWidgets
from qtpy.QtWidgets import QMessageBox, QDialogButtonBox, QDialog

from pymodaq_utils.logger import set_logger, get_module_name

from pymodaq_gui.managers.parameter_manager import ParameterManager
from pymodaq_gui.parameter import ioxml, Parameter
from pymodaq_gui.utils import select_file
from pymodaq_gui.messenger import dialog as dialogbox


logger = set_logger(get_module_name(__file__))


class ConfigManager(ParameterManager):
    """
    Manager class for handling configuration files and parameters.

    Provides functionality to create, load, modify, and save configuration
    files in XML format with a graphical user interface.

    Attributes:
        title (str): Display title for the configuration manager
        name (str): Internal name for the configuration manager
        config_path (Path): Path to the directory containing config files
    """

    title = "Config"
    name = "config"

    def __init__(self, config_path: Path = "", msgbox=False):
        """
        Initialize the ConfigManager.

        Args:
            config_path (Path, optional): Path to the configuration directory. Defaults to ''.
            msgbox (bool, optional): If True, shows a dialog box on initialization asking
                whether to create a new config or modify an existing one. Defaults to False.
        """
        super().__init__(settings_name=self.name)
        self.config_path = config_path
        if msgbox:
            msgBox = QMessageBox()
            msgBox.setText(f"{self.title} Manager")
            msgBox.setInformativeText("What do you want to do?")
            cancel_button = msgBox.addButton(QMessageBox.StandardButton.Cancel)
            new_button = msgBox.addButton("New", QMessageBox.ButtonRole.ActionRole)
            modify_button = msgBox.addButton("Modify", QMessageBox.ButtonRole.AcceptRole)
            msgBox.setDefaultButton(QMessageBox.StandardButton.Cancel)
            ret = msgBox.exec()

            if msgBox.clickedButton() == new_button:
                self.set_new_config()

            elif msgBox.clickedButton() == modify_button:
                path = select_file(start_path=config_path, save=False, ext="xml")
                if path != "":
                    self.set_config_from_file(str(path))
            else:  # cancel
                pass

    def make_config(self):
        """
        Create additional configuration parameters.

        Method to be subclassed to add custom parameters specific to
        the configuration needs of derived classes.

        Returns:
            list: List of parameter dictionaries to be added to the configuration.
                Empty list in base implementation.
        """
        return []

    def set_new_config(self, file: str = None, show=True):
        """
        Create a new configuration with default parameters.

        Opens a dialog allowing the user to set up a new configuration file
        with a filename and any additional parameters defined in make_config().

        Args:
            file (str, optional): Default filename for the new config.
                If None, uses "{title}_default". Defaults to None.
        """
        if file is None:
            file = f"{self.title}_default"
        param = [
            {"title": "Filename:", "name": "filename", "type": "str", "value": file},
        ]
        additional_params = self.make_config()
        self.settings = Parameter.create(
            title=f"{self.title}",
            name=f"{self.name}",
            type="group",
            children=param + additional_params,
        )
        logger.info("Creating a new remote file")
        if show:
            self.show_config()

    def set_config_from_file(self, file_path: Path, show=True):
        """
        Load an existing configuration from an XML file.

        Reads an XML configuration file and populates the settings tree
        with the parameters from the file.

        Args:
            file_path (Path): Path to the XML configuration file to load.
            show (bool, optional): If True, displays the configuration dialog
                after loading. Defaults to True.

        Note:
            If file_path is not a Path object, it will be converted to one.
            Only XML files are supported.
        """
        if not isinstance(file_path, Path):
            file_path = Path(file_path)
        if file_path.suffix == ".xml":
            children = ioxml.XML_file_to_parameter(file_path)
        else:
            logger.exception("file_path must be of xml type")
            return

        self.settings = Parameter.create(
            title=f"{self.title}",
            name=f"{self.name}",
            type="group",
            children=children,
        )
        if show:
            self.show_config()

    def show_config(self, widget=None, overwrite=False):
        """
        Display the configuration dialog for viewing and editing settings.

        Creates and shows a modal dialog containing the settings tree with
        Save and Cancel buttons. If the user clicks Save, the configuration
        is saved to file.

        Args:
            widget (QtWidgets.QWidget, optional): Additional widget to include
                in the dialog layout. Defaults to None.
            overwrite (bool, optional): If True, overwrites existing files without
                prompting. Defaults to False.
        Returns:
            bool: True if the file was successfully saved, False otherwise.
        """
        dialog = QDialog()
        vlayout = QtWidgets.QVBoxLayout()

        vlayout.addWidget(self.settings_tree)
        dialog.setLayout(vlayout)
        buttonBox = QDialogButtonBox(parent=dialog)

        buttonBox.addButton("Save", QDialogButtonBox.ButtonRole.AcceptRole)
        buttonBox.accepted.connect(dialog.accept)
        buttonBox.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)
        buttonBox.rejected.connect(dialog.reject)

        vlayout.addWidget(buttonBox)
        dialog.setWindowTitle("Fill in information about this managers")

        if widget is not None and isinstance(widget, QtWidgets.QWidget):
            vlayout.addWidget(widget)

        res = dialog.exec()
        if res == QDialog.DialogCode.Accepted:
            return self.save_config(overwrite)
    
    def save_config(self, overwrite=False):
        """
        Save the current configuration to an XML file.

        Saves the settings to an XML file in the config_path directory using
        the filename specified in the settings. If the file already exists and
        overwrite is False, prompts the user for confirmation before overwriting.

        Args:
            overwrite (bool, optional): If True, overwrites existing files without
                prompting. If False, asks for user confirmation before overwriting.
                Defaults to False.

        Returns:
            bool: True if the file was successfully saved, False otherwise.

        Note:
            The filename is retrieved from the 'filename' parameter in settings.
            The file is saved with a .xml extension in the config_path directory.
        """
        filename = self.settings.child("filename").value()       
        saved = False
        try:
            ioxml.parameter_to_xml_file(self.settings, self.config_path.joinpath(filename), overwrite=overwrite)
            saved = True
        except FileExistsError as currenterror:
            logger.warning(f"{currenterror} File {filename}.xml exists")
            user_agreed = dialogbox(
                title="Overwrite confirmation",
                message="File exist do you want to overwrite it ?",
            )
            if user_agreed:
                ioxml.parameter_to_xml_file(self.settings, self.config_path.joinpath(filename))
                logger.warning(f"File {filename}.xml overwriten at user request")
                saved = True
            else:
                logger.warning(f"File {filename}.xml wasn't saved at user request")

        return saved
