def categorize_items(item_list, remote_items=None, mock_items=None):
    """
    Core function: categorize any list of items into Mock/Plugin/Remote.

    Args:
        item_list: List of items to categorize
        remote_items: Custom set of remote items (optional)
        mock_items: Custom set of mock items (optional)

    Returns: dict {category: [items]} with only non-empty categories
    """
    remote_items = remote_items or REMOTE_ITEMS
    mock_items = mock_items or MOCK_ITEMS

    categorized = {'Remote': [], 'Mock': [], 'Plugin': []}

    for item in item_list:
        if item in remote_items:
            categorized['Remote'].append(item)
        elif item in mock_items or 'mock' in item.lower():
            categorized['Mock'].append(item)
        else:
            categorized['Plugin'].append(item)

    # Return only non-empty categories
    return {k: v for k, v in categorized.items() if v}


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
MOCK_ITEMS = {}


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
