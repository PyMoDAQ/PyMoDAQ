from pymodaq_utils.config import GlobalConfig
from pymodaq_data import Q_


config = GlobalConfig()



def get_unit_to_display(unit: str) -> str:
    """Get the unit to be displayed in the UI

    If the controller units are in mm the displayed unit will be m
    because m is the base unit, then the user could ask for mm, km, µm...
    only issue is when the usual displayed unit is not the base one, then add cases below

    Parameters
    ----------
    unit: str

    Returns
    -------
    str: the unit to be displayed on the ui
    """
    if ("°" in unit or "degree" in unit) and not "°C" in unit:
        # special case as pint base unit for angles are radians
        return "°"
    elif "°C" in unit:
        return "°C"
    else:
        for key in config("pymodaq", "actuator", "allowed_units"):
            if key in unit:
                return config("pymodaq", "actuator", "allowed_units", key)
        return str(Q_(1, unit).to_base_units().units)