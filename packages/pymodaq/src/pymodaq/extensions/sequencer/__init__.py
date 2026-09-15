# -*- coding: utf-8 -*-
"""
Created the 01/06/2023

@author: Sebastien Weber
"""
from pymodaq.extensions.sequencer.utilities.choice_models.model import get_choice_models
from pymodaq.extensions.sequencer.utilities.element_factory import register_elements
from pymodaq_utils.config import get_set_config_dir

elts = register_elements()
get_choice_models()  # register choice models
pass

def get_set_sequencer_path(subfolder: str = '', user=False):
    """ creates and return the config folder path for managers files
    """
    target_path = get_set_config_dir('sequences', user=user).joinpath(subfolder)
    target_path.mkdir(parents=True, exist_ok=True)

    return target_path