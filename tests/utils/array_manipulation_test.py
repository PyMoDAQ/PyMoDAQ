import numpy as np
import pytest

from pymodaq.utils import array_manipulation as array


def test_random_step():
    pos_array = array.random_step(0, 10, 1)
    for value in pos_array:
        assert 0 <= value <= 10
        
    neg_array = array.random_step(0, -10, -1)
    for value in neg_array:
        assert -10 <= value <= 0
    
    with pytest.raises(ValueError):
        array.random_step(1, 10, 0)
    with pytest.raises(ValueError):
        array.random_step(1, 10, -1)
    with pytest.raises(ValueError):
        array.random_step(-1, -10, 1)


def test_linspace_this_vect():
    test_x = [0.0, 1.1, 2.2, 3.3, 10]
    linear_x = array.linspace_this_vect(test_x)
    result_x = [0, 2.5, 5, 7.5, 10]
    assert np.size(linear_x) == 5
    assert np.array_equal(linear_x, result_x)
    
    test_y = [0.0, 0.55, 1.1, 1.65, 5]
    linear_x, linear_y = array.linspace_this_vect(test_x, y=test_y)
    result_y = [0, 1.25, 2.5, 3.75, 5]
    assert np.array_equal(linear_x, result_x)
    assert np.array_equal(linear_y, result_y)
    
    linear_dim = array.linspace_this_vect(test_x, Npts = 11)
    result_dim = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert np.size(linear_dim) == 11
    assert np.array_equal(linear_dim, result_dim)


def test_find_index():
    test_array = np.array([1, 2, 3, 4, 5, 10, 20, 30, 40, 200, 2000])
    values = [3.25, 27, 39, 1000, 5000, -10]
    indexes_found = array.find_index(test_array, values)
    results = [(2, 3), (7, 30), (8, 40), (9, 200), (10, 2000), (0, 1)]
    assert np.array_equal(indexes_found, results)

    value = 15.5
    index_found = array.find_index(test_array, value)
    result = [(6, 20)]
    assert np.array_equal(index_found, result)


def test_find_rising_edges():
    test_x = np.array([3, 2, 1, 2, 3, 4, 5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 6, 5])
    indexes_found = array.find_rising_edges(test_x, 1.1)
    results = [([2, 12], np.array([1, 1]))]
    assert np.array_equal(indexes_found, results)
    
    indexes_found = array.find_rising_edges(test_x, [1.1, 5.5])
    results = [([2, 12], np.array([1, 1])), ([15], np.array([4]))]
    for array1, array2 in zip(indexes_found, results):
        assert np.array_equal(array1, array2)


def test_crop_vector_to_axis():
    test_x = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    test_V = np.array([12.5, 13, 12, 11, 9.8, 9.5, 9, 10.1, 10.3, 10.8, 11])
    cropped_x, cropped_V = array.crop_vector_to_axis(test_x, test_V, [3, 7])
    result_x = np.array([3, 4, 5, 6, 7])
    result_V = np.array([12, 11, 9.8, 9.5, 9])
    assert np.array_equal(cropped_x, result_x)
    assert np.array_equal(cropped_V, result_V)

    cropped_x, cropped_V = array.crop_vector_to_axis(test_x, test_V, [7, 3])
    assert np.array_equal(cropped_x, result_x)
    assert np.array_equal(cropped_V, result_V)


def test_rescale():
    test_x = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    rescaled_x = array.rescale(test_x)
    result = np.array([0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1])
    for val1, val2 in zip(rescaled_x, result):
        assert pytest.approx(val1) == val2
        
    rescaled_x = array.rescale(test_x, [1, 0])
    result = np.flip(result)
    for val1, val2 in zip(rescaled_x, result):
        assert pytest.approx(val1) == val2
    
    rescaled_x = array.rescale(test_x, [0, 5])
    result = np.array([0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5])
    for val1, val2 in zip(rescaled_x, result):
        assert pytest.approx(val1) == val2


def test_marginals():
    test_x = np.array([[1, 2, 3], [0.1, 0.2, 0.3]])
    marginalised = array.marginals(test_x)
    result = tuple([np.array([6, 0.6]), np.array([1.1, 2.2, 3.3])])
    for array1, array2 in zip(marginalised, result):
        for val1, val2 in zip(array1, array2):
            assert pytest.approx(val1) == val2
    
    marginalised = array.marginals(test_x, axes=[2])
    assert marginalised == 6.6
    
    marginalised = array.marginals(test_x, normalize=True)
    result = tuple([np.array([1, 0]), np.array([0, 0.5, 1])])
    for array1, array2 in zip(marginalised, result):
        for val1, val2 in zip(array1, array2):
            assert pytest.approx(val1) == val2


def test_find():
    test_x = np.array([1, 2, 3, -1, 4])
    is_positive = lambda x: x > 0
    assert array.find(test_x, is_positive, 4) == 4
    
    test_x = np.array([-1, -2, -3, -4, -5])
    assert array.find(test_x, is_positive, 1) == -1
    
    is_negative = lambda x: x < 0
    assert  array.find(test_x, is_negative) == 0


def test_arglimit():
    test_x = np.array([1, 2, 3, 4, 5, 6])
    assert array.arglimit(test_x) == tuple([0, 5])
    
    test_x = np.array([1e4, 1e3, 100, 10, 1, 0.1, 0.01])
    assert array.arglimit(test_x) == tuple([0, 3])
    assert array.arglimit(test_x, threshold=0.15) == tuple([0, 0])
    assert array.arglimit(test_x, threshold=10) == tuple([0, 6])

def test_limit():
    test_x = np.array([1, 2, 3, 4, 5, 6])
    test_y = np.array([1e4, 1e3, 100, 10, 1, 0.1])
    assert array.limit(test_x) == tuple([-0.25, 7.25])
    assert array.limit(test_x, y=test_y) == tuple([0.25, 4.75])
    assert array.limit(test_x, extend=False) == tuple([1, 6])
    assert array.limit(test_x, y=test_y, extend=False) == tuple([1, 4.75])


def test_crop_array_to_axis():
    test_x = np.array([1, 2, 3, 4])
    test_y = np.array([0.1, 0.2, 0.3, 0.4])
    test_M = np.array([[0.1, 0.2, 0.3, 0.4],
                       [1, 2, 3, 4],
                       [10, 20, 30, 40],
                       [100, 200, 300, 400]])
    cropbox = np.array([2, 4, 0.1, 0.3])
    cropped = array.crop_array_to_axis(test_x, test_y, test_M, cropbox)
    result = tuple([test_x[1:], test_y[:3], test_M[:3, 1:]])
    for array1, array2 in zip(cropped, result):
        assert np.array_equal(array1, array2)

    cropbox = np.array([4, 2, 0.3, 0.1])
    cropped = array.crop_array_to_axis(test_x, test_y, test_M, cropbox)
    for array1, array2 in zip(cropped, result):
        assert np.array_equal(array1, array2)
    


def test_interp1D():
    x = np.linspace(1, 10, 10)
    xlin = np.linspace(10, 1, 10)
    M = np.linspace(x, x + 90, 10)
    result = array.interp1D(x, M, xlin, axis=0)
    expected = np.linspace(x + 90, x, 10)
    assert np.array_equal(result, expected)

    result = array.interp1D(x, M, xlin, axis=1)
    expected = np.linspace(xlin, xlin + 90, 10)
    assert np.array_equal(result, expected)


def test_linspace_this_image():
    x = np.linspace(1, 10, 10)
    M = np.linspace(x, x + 90, 10)
    result = array.linspace_this_image(x, M)
    assert np.array_equal(result[1], M)

    y = np.linspace(10, 1, 10)
    result = array.linspace_this_image(y, M, axis=0)
    expected = np.append([x], np.linspace(x + 90, x + 90, 9), axis=0)
    assert np.array_equal(result[1], expected)


def test_max_ind():
    test_x = [10, 17, 13, 17.2, 4, -30]
    assert array.max_ind(test_x) == tuple([3, 17.2])
    
    test_x = [[10, 17, 13, 17.2, 4, -30], [1, 7, 3, 9, -4, -12]]
    max_ind = array.max_ind(test_x, axis=0)
    result = tuple([np.array([0, 0, 0, 0, 0, 1]), np.array([10, 17, 13, 17.2, 4, -12])])
    for array1, array2 in zip(max_ind, result):
        assert np.array_equal(array1, array2)
        
    max_ind = array.max_ind(test_x, axis=1)
    result = tuple([np.array([3, 3]), np.array([17.2, 9])])
    for array1, array2 in zip(max_ind, result):
        assert np.array_equal(array1, array2)


def test_min_ind():
    test_x = [10, 17, 13, 17.2, 4, -30]
    assert array.min_ind(test_x) == tuple([5, -30])

    test_x = [[10, 17, 13, 17.2, 4, -30], [1, 7, 3, 9, -4, -12]]
    min_ind = array.min_ind(test_x, axis=0)
    result = tuple([np.array([1, 1, 1, 1, 1, 0]), np.array([1, 7, 3, 9, -4, -30])])
    for array1, array2 in zip(min_ind, result):
        assert np.array_equal(array1, array2)

    min_ind = array.min_ind(test_x, axis=1)
    result = tuple([np.array([5, 5]), np.array([-30, -12])])
    for array1, array2 in zip(min_ind, result):
        assert np.array_equal(array1, array2)