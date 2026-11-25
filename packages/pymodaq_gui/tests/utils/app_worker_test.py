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
                return super().prepare_data_to_save(bundle)

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
