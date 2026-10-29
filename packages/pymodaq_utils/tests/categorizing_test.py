from pymodaq_utils.categorizing import categorize_items, add_category_layers, flatten_categories


class TestCategorizeItems:
    def test_simulated_instruments_are_under_one_banner(self):
        categorized = categorize_items(['Mock', 'MockSpectro', 'BSCamera', 'CookbookDll', 'FakeStage', 'Andor'])
        assert list(categorized) == ['Mock', 'Plugin']
        assert categorized['Mock'] == ['Mock', 'MockSpectro', 'BSCamera',
                                       {'Cookbook': ['CookbookDll']}, {'Fake': ['FakeStage']}]
        assert categorized['Plugin'] == ['Andor']

    def test_remote_instruments_have_their_category(self):
        assert categorize_items(['LECODirector', 'TCPServer', 'Andor']) == {
            'Remote': ['LECODirector', 'TCPServer'], 'Plugin': ['Andor']}

    def test_bs_is_a_prefix_of_the_beam_steering_family_only(self):
        categorized = categorize_items(['BSPiezoMirror', 'BSpline'])
        assert categorized == {'Mock': ['BSPiezoMirror'], 'Plugin': ['BSpline']}

    def test_empty_categories_are_dropped(self):
        assert categorize_items(['Andor']) == {'Plugin': ['Andor']}
        assert categorize_items([]) == {}

    def test_the_dimension_is_a_layer_above_the_categories(self):
        layered = add_category_layers({'DAQ0D': ['Mock', 'CookbookDll'], 'DAQ1D': ['Andor']})
        assert layered == {'DAQ0D': {'Mock': ['Mock', {'Cookbook': ['CookbookDll']}]},
                           'DAQ1D': {'Plugin': ['Andor']}}

    def test_flatten_gives_the_banners_above_each_name(self):
        flat = flatten_categories(categorize_items(['Mock', 'CookbookDll', 'TCPServer', 'Andor']))
        assert flat == [(('Remote',), 'TCPServer'), (('Mock',), 'Mock'), (('Mock', 'Cookbook'), 'CookbookDll'),
                        (('Plugin',), 'Andor')]
