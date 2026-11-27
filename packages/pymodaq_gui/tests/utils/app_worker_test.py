from types import SimpleNamespace

import numpy as np

from pymodaq_data import DataToExport, DataWithAxes
from pymodaq_data.h5modules.data_saving import DataBundle
from pymodaq_gui.managers.runner_thread_manager import ThreadWorker
from pymodaq_gui.utils.app_worker import ExtensionWorker


def make_bundle() -> DataBundle:
    dwa = DataWithAxes('data', source='raw', data=[np.arange(3.)])
    return DataBundle(dte=DataToExport('dte', data=[dwa]), save_index=0)


def make_worker(worker_class=ExtensionWorker):
    """ An extension worker whose 'saver' is a ThreadWorker, only used for its data_to_save_signal"""
    worker = worker_class(SimpleNamespace())
    worker.saver_worker = ThreadWorker()
    received = []
    worker.saver_worker.data_to_save_signal.connect(received.append)
    return worker, received


class TestPrepareDataToSave:

    def test_default_hook_returns_the_bundle_unchanged(self):
        worker, _ = make_worker()
        bundle = make_bundle()
        assert worker.prepare_data_to_save(bundle) is bundle

    def test_emit_data_to_save_sends_the_bundle(self):
        worker, received = make_worker()
        bundle = make_bundle()

        worker.emit_data_to_save(bundle)

        assert received == [bundle]

    def test_hook_is_called_before_emission_and_its_result_is_emitted(self):
        calls = []

        class AnnotatingWorker(ExtensionWorker):
            def prepare_data_to_save(self, bundle):
                calls.append(bundle)
                for dwa in bundle.dte:
                    dwa.add_extra_attribute(quantity_kind='some_iri')
                return bundle

        worker, received = make_worker(AnnotatingWorker)
        bundle = make_bundle()

        worker.emit_data_to_save(bundle)

        assert calls == [bundle]
        assert len(received) == 1
        assert received[0].dte[0].quantity_kind == 'some_iri'
        assert 'quantity_kind' in received[0].dte[0].extra_attributes

    def test_hook_can_return_another_bundle(self):
        replacement = make_bundle()

        class ReplacingWorker(ExtensionWorker):
            def prepare_data_to_save(self, bundle):
                return replacement

        worker, received = make_worker(ReplacingWorker)

        worker.emit_data_to_save(make_bundle())

        assert received == [replacement]


class TestDataPreparers:

    def test_registered_function_acts_on_the_bundle_before_emission(self):
        worker, received = make_worker()

        def annotate(bundle):
            for dwa in bundle.dte:
                dwa.add_extra_attribute(quantity_kind='some_iri')  # modified in place, returns None

        worker.add_data_preparer(annotate)
        worker.emit_data_to_save(make_bundle())

        assert len(received) == 1
        assert received[0].dte[0].quantity_kind == 'some_iri'

    def test_functions_are_called_in_order_and_may_replace_the_bundle(self):
        worker, received = make_worker()
        calls = []
        replacement = make_bundle()

        def first(bundle):
            calls.append('first')
            return replacement

        def second(bundle):
            calls.append(('second', bundle is replacement))

        worker.add_data_preparer(first)
        worker.add_data_preparer(second)
        worker.emit_data_to_save(make_bundle())

        assert calls == ['first', ('second', True)]
        assert received == [replacement]

    def test_function_registered_twice_is_called_once(self):
        worker, _ = make_worker()
        calls = []

        def preparer(bundle):
            calls.append(1)

        worker.add_data_preparer(preparer)
        worker.add_data_preparer(preparer)
        worker.emit_data_to_save(make_bundle())

        assert calls == [1]

    def test_removed_function_is_not_called(self):
        worker, _ = make_worker()
        calls = []

        def preparer(bundle):
            calls.append(1)

        worker.add_data_preparer(preparer)
        worker.remove_data_preparer(preparer)
        worker.remove_data_preparer(preparer)  # ignored
        worker.emit_data_to_save(make_bundle())

        assert calls == []

    def test_registered_functions_saving_before_the_hook_without_super(self):
        calls = []

        class MyWorker(ExtensionWorker):
            def prepare_data_to_save(self, bundle):
                calls.append('hook')
                return bundle

        worker, _ = make_worker(MyWorker)
        worker.add_data_preparer(lambda bundle: calls.append('preparer'))
        worker.emit_data_to_save(make_bundle())

        assert calls == ['preparer', 'hook']


class TestSavingEnd:
    """The worker takes the picture of its saving and tells the app that this saving is over"""

    def make(self, tmp_path, saving_id='abc'):
        calls = []
        state = SimpleNamespace(saving_id=saving_id)
        app = SimpleNamespace(
            current_saving_id=lambda: state.saving_id,
            take_saving_snapshot=lambda saving: tmp_path / f'{saving}.png',
            notify_saving_end=lambda path, saving: calls.append((path, saving)))
        worker = ExtensionWorker(app)
        worker._saving_id = worker._current_saving_id()
        return worker, calls, state

    def test_saving_is_the_one_known_when_the_worker_started(self, tmp_path):
        worker, _, _ = self.make(tmp_path)
        assert worker._saving_id == 'abc'

    def test_picture_and_saving_id_are_given_to_the_app(self, tmp_path):
        worker, calls, _ = self.make(tmp_path)

        snapshot = worker._take_snapshot()
        worker._end_saving(snapshot)

        assert calls == [(tmp_path / 'abc.png', 'abc')]

    def test_a_saving_is_ended_once(self, tmp_path):
        worker, calls, _ = self.make(tmp_path)

        worker._end_saving(None)
        worker._end_saving(None)

        assert len(calls) == 1

    def test_a_worker_ends_its_own_saving_even_if_another_one_started(self, tmp_path):
        worker, calls, state = self.make(tmp_path)
        state.saving_id = 'next'  # the next scan of a batch

        worker._end_saving(None)

        assert calls == [(None, 'abc')]

    def test_app_without_saving_is_left_alone(self, tmp_path):
        worker, calls, _ = self.make(tmp_path, saving_id=None)

        assert worker._saving_id is None
        assert worker._take_snapshot() is None
        worker._end_saving(None)
        assert calls == []
