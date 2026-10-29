import re


def _is_mock(item: str, mock_items) -> bool:
    """Simulated instruments: the mock ones, and the beam steering family (BSCamera, BSPiezoMirror...)"""
    return item in mock_items or 'mock' in item.lower() or re.match(r'BS[A-Z]', item) is not None


def categorize_items(item_list, remote_items=None, mock_items=None):
    """
    Core function: categorize any list of items into Remote/Mock/Plugin.

    The ``Mock`` category groups all the simulated instruments under one banner: the ones whose name contains
    ``mock`` or starts with ``BS`` (beam steering demonstrations) are leaves of it, the ``Cookbook`` recipes and the
    ``Fake`` ones (name containing ``fake``) are in a submenu of their own.

    Args:
        item_list: List of items to categorize
        remote_items: Custom set of remote items (optional)
        mock_items: Custom set of mock items (optional)

    Returns: dict {category: [items]} with only non-empty categories. The items of the ``Mock`` category are names or
    single-key dicts ``{'Cookbook': [names]}`` (a submenu), as understood by
    :func:`pymodaq_gui.utils.menu_utils.build_menu_from_iterable`.
    """
    remote_items = remote_items or REMOTE_ITEMS
    mock_items = mock_items or MOCK_ITEMS

    remote, plugin, mock, cookbook, fake = [], [], [], [], []

    for item in item_list:
        if item in remote_items:
            remote.append(item)
        elif item.startswith('Cookbook'):
            cookbook.append(item)
        elif 'fake' in item.lower():
            fake.append(item)
        elif _is_mock(item, mock_items):
            mock.append(item)
        else:
            plugin.append(item)

    mock_group = list(mock)
    for name, items in (('Cookbook', cookbook), ('Fake', fake)):
        if items:
            mock_group.append({name: items})

    categorized = {'Remote': remote, 'Mock': mock_group, 'Plugin': plugin}

    # Return only non-empty categories
    return {k: v for k, v in categorized.items() if v}


def flatten_categories(categorized: dict) -> list:
    """Flatten the result of :func:`categorize_items` to a list of ``(path, name)``

    ``path`` is the tuple of the banners above ``name``, for instance ``('Mock', 'Cookbook')``.
    """
    flat = []

    def visit(items, path):
        for item in items:
            if isinstance(item, dict):
                for key, sub_items in item.items():
                    visit(sub_items, path + (key,))
            else:
                flat.append((path, item))

    for category, items in categorized.items():
        visit(items, (category,))
    return flat


def add_category_layers(dimension_dict, remote_items=None, mock_items=None):
    """
    Add category layers to a dimension dictionary.
    Uses categorize_items for each dimension.

    Args:
        dimension_dict: {dimension: [items]}

    Returns: {dimension: {category: [items]}}
    """
    result = {}

    for dimension, items in dimension_dict.items():
        # Reuse the core categorization function
        result[dimension] = categorize_items(items, remote_items, mock_items)

    return result


REMOTE_ITEMS = {'LECODirector', 'TCPServer'}
MOCK_ITEMS = set()


def find_last_index(list_children: list = None, name_prefix='', format_string='02.0f'):
    if list_children is None:
        list_children = []
    # Custom function to find last available index
    child_indexes = ([int(par.name()[len(name_prefix):]) for par in list_children if name_prefix in par.name()])
    if len(child_indexes) == 0:
        newindex = 0
    else:
        newindex = max(child_indexes) + 1
    return f'{newindex:{format_string}}'
