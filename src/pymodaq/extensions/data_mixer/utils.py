from pymodaq_utils.config import BaseConfig


class DataMixerConfig(BaseConfig):
    """Main class to deal with configuration values for this plugin

    To b subclassed for real implementation if needed, see Optimizer class attribute config_saver
    """
    config_template_path = None
    config_name = f"datamixer_settings"


def find_key_in_nested_dict(dic, key):
    stack = [dic]
    while stack:
        d = stack.pop()
        if key in d:
            return d[key]
        for v in d.values():
            if isinstance(v, dict):
                stack.append(v)
            if isinstance(v, list):
                stack += v
