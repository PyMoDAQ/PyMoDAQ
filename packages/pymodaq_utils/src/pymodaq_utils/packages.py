from hashlib import sha256
from importlib import metadata
from typing import Union, List

import requests
from lxml import html
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from pymodaq_utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


def get_pypi_package_list(match_name: Union[str, list[str]] = None,
                          print_method=logger.info) -> List[str]:
    """Connect to the "simple" pypi url to get the list of all packages matching all or part of
    the given name

    Parameters
    ----------
    match_name: str
        The package name to be (partially) matched
    print_method: Callable

    Examples
    --------
    get_pypi_package_list('pymodaq_plugins') will retrieve the names of all packages having 'pymodaq_plugins'
    in their name
    """
    if isinstance(match_name, str):
        match_name = [match_name]
    status = 'Connecting to the pypi repository, may take some time to retrieve the list'
    print_method(status)
    simple_package = requests.get('https://pypi.org/simple/')
    if simple_package.status_code == 503:
        info = 'The service from pypi is currently unavailable, please retry later or install your plugins manually'
        print_method(info)
    tree = html.fromstring(simple_package.text)
    packages = []
    for child in tree.body:
        if match_name is None or all([name in child.text for name in match_name]):
            packages.append(child.text)
            print_method(f'Got package {child.text}')
    return packages


def get_pymodaq_specifier(requirements: List[str]) -> SpecifierSet:
    """Get specifiers for pymodaq version from a list of requirements"""
    specifier = SpecifierSet('>3.0,<4.0')
    if requirements is not None:
        for package in requirements:
            req = Requirement(package)
            if req.name == 'pymodaq':
                specifier = req.specifier
                break
    return specifier


def get_package_metadata(name: str, version: Union[str, Version] = None) -> dict:
    """Retrieve the metadata of a given package on pypi matching or not a specific version

    Parameters
    ----------
    name: str
        package name
    version: Union[str, Version]
        package version specifier


    Returns
    -------
    dict of metadata
    """
    if version is None:
        url = f'https://pypi.python.org/pypi/{name}/json'
    else:
        url = f'https://pypi.python.org/pypi/{name}/{str(version)}/json'
    rep = requests.get(url)
    if rep.status_code != 404:
        return rep.json()


def get_metadata_from_json(json_as_dict: dict) -> dict:
    """Transform dict of metadata from pypi to a simpler dict"""
    try:
        if json_as_dict is not None:
            metadata = dict([])
            metadata['author'] = json_as_dict['info']['author']
            metadata['description'] = json_as_dict['info']['description']
            metadata['project_url'] = json_as_dict['info']['project_url']
            metadata['version'] = json_as_dict['info']['version']
            metadata['requirements'] = json_as_dict['info']['requires_dist']
            return metadata
    except:
        pass


def get_pypi_pymodaq(package_name='pymodaq-plugins', pymodaq_version: Version = None, pymodaq_latest: Version = None):
    """ Get the latest plugin info compatible with a given version of pymodaq

    Parameters
    ----------
    package_name: str
    pymodaq_version: Version

    Returns
    -------
    dict containing metadata of the latest compatible plugin
    """
    if package_name == 'pymodaq-plugins':  # has been renamed pymodaq-plugins-mock
        return
    if isinstance(pymodaq_version, str):
        pymodaq_version = Version(pymodaq_version)
    if pymodaq_latest is None:
        pymodaq_latest = Version(list(get_package_metadata('pymodaq')['releases'].keys())[-1])
    latest = get_package_metadata(package_name)
    if latest is not None:
        if pymodaq_version is not None:
            versions = list(latest['releases'].keys())[::-1]
            for _version in versions:
                versioned = get_package_metadata(package_name, _version)
                if versioned is not None:
                    specifier = get_pymodaq_specifier(versioned['info']['requires_dist'])
                    if str(specifier) == '>=2.0':  # very old stuff
                        return
                    if pymodaq_version.base_version in specifier:
                        return get_metadata_from_json(versioned)
                    elif pymodaq_latest == pymodaq_version:  # if not in specifier and requested pymodaq version is
                        # latest, not need to loop into older package versions, they won't be compatible either
                        return
        else:
            return get_metadata_from_json(latest)


def get_check_repo(plugin_dict):
    """Unused"""
    try:
        response = requests.get(plugin_dict["repository"])
    except requests.exceptions.RequestException as e:
        logger.exception(str(e))
        return str(e)

    if response.status_code != 200:
        rep = f'{plugin_dict["display-name"]}: failed to download plugin. Returned code {response.status_code}'
        logger.error(rep)

    # Hash it and make sure its what is expected
    hash = sha256(response.content).hexdigest()
    if plugin_dict["id"].lower() != hash.lower():
        rep = f'{plugin_dict["display-name"]}: Invalid hash. Got {hash.lower()} but expected {plugin_dict["id"]}'
        logger.error(rep)
        return rep
    else:
        logger.info(f'SHA256 is Ok')


def get_entrypoints(group='pymodaq.plugins'):
    """ Get the list of modules defined from a group entry point

    Because of evolution in the package, one or another of the forms below may be deprecated.
    We start from the newer way down to the older

    Parameters
    ----------
    group: str
        the name of the group
    """
    try:
        discovered_entrypoints = metadata.entry_points(group=group)
    except TypeError:
        try:
            discovered_entrypoints = metadata.entry_points().select(group=group)
        except AttributeError:
            discovered_entrypoints = metadata.entry_points().get(group, [])
    if isinstance(discovered_entrypoints, tuple):  # API for python > 3.8
        discovered_entrypoints = list(discovered_entrypoints)
    return discovered_entrypoints


def post_error(message):
    logger.error(message)


def extract_authors_from_description(description):
    """returns the authors as a list from the plugin package description (it should follow the template structure)

    Parameters
    ----------
    description: (str)

    Returns
    -------
    list of string
    """

    posa = description.find('Authors')
    pos_if_need = description.find('\n\n.. if needed use this field')
    posc = description.find('\n\nContributors')
    posi = description.find('\n\nInstruments')
    if posi == -1:
        posi = description.find('\nInstruments')  # in case only one new line has been used
        if posi == -1:
            posi = description.find('Instruments')
            if posi == -1:
                posi == posa + 50

    authors_end = pos_if_need if pos_if_need != -1 else posc
    if authors_end == -1 or authors_end > posi:
        authors_end = posi

    authors_raw = description[posa:authors_end]
    return authors_raw.split('\n* ')[1:]
