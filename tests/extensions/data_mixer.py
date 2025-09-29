from pymodaq.extensions.data_mixer.model import get_models



def test_get_models():
    models = get_models()
    pass
    assert len(models) >= 2
    assert 'DataMixerGaussianFitModel' in [model['class'].__name__ for model in models]
    assert 'DataMixerModelEquation' in [model['class'].__name__ for model in models]