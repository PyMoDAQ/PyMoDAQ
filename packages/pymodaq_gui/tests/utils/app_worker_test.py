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

    def test_registered_functions_run_before_the_hook_without_super(self):
        calls = []

        class MyWorker(ExtensionWorker):
            def prepare_data_to_save(self, bundle):
                calls.append('hook')
                return bundle

        worker, _ = make_worker(MyWorker)
        worker.add_data_preparer(lambda bundle: calls.append('preparer'))
        worker.emit_data_to_save(make_bundle())

        assert calls == ['preparer', 'hook']


class TestRunEnd:
    """The worker takes the picture of the extension and tells the saver that the run is over"""

    def make(self, tmp_path, picture=True):
        calls = []
        saver = SimpleNamespace(snapshot_file_path=lambda: tmp_path / 'run.png',
                                end_run=lambda path: calls.append(path))
        app = SimpleNamespace(module_and_data_saver=saver)
        if picture:
            app.save_snapshot = lambda path: path
        worker = ExtensionWorker(app)
        return worker, calls

    def test_picture_path_is_given_to_the_saver(self, tmp_path):
        worker, calls = self.make(tmp_path)

        snapshot = worker._take_snapshot()
        worker._end_run(snapshot)

        assert calls == [tmp_path / 'run.png']

    def test_no_picture_if_the_app_cannot_take_one(self, tmp_path):
        worker, calls = self.make(tmp_path, picture=False)

        assert worker._take_snapshot() is None
        worker._end_run(None)
        assert calls == [None]

    def test_saver_without_runs_is_left_alone(self):
        worker = ExtensionWorker(SimpleNamespace(module_and_data_saver=SimpleNamespace()))

        assert worker._take_snapshot() is None
        worker._end_run(None)  # nothing to call, no error
