import re
from typing import List


data_name_regexp = re.compile(r"({.*?})+")  # first occurrences of things between {}


def split_formulae(formulae: str) -> List[str]:
    """ Split a string into a list of string for each new line

    Parameters
    ----------
    formulae: str
        The formulae containing various mathematical formula separated with a new line character

    Returns
    -------
    The various formula as a list of string
    """
    return re.split(r'\n', formulae)


def extract_data_names(formula: str) -> List[str]:
    """ Extract the names of the data appearing between curly brackets with a given string formula

    Parameters
    ----------
    formula: str
        The mathematical expression to compute containing in curly brackets the data full names

    Returns
    -------

    """
    data_names = [data_name_with_curly[1:-1] for
                  data_name_with_curly in data_name_regexp.findall(formula)]
    return data_names


def replace_names_in_formula(formula: str):
    formula_tmp = formula[:]
    names = []
    while True:
        m = data_name_regexp.search(formula_tmp)
        if m is not None:
            names.append(m.group())
            formula_tmp = (
                formula_tmp.replace(formula_tmp[m.start(): m.end()],
                                    f'dte.get_data_from_full_name("{m.group()[1:-1]}")'))
        else:
            break
    return formula_tmp, names

