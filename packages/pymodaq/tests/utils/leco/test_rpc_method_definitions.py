import pytest
from pyleco.json_utils.json_objects import Request

from pymodaq.utils.leco.daq_move_LECODirector import DAQ_Move_LECODirector
from pymodaq.utils.leco.daq_xDviewer_LECODirector import DAQ_xDViewer_LECODirector
from pymodaq.utils.leco.rpc_method_definitions import (
    GenericDirectorMethods,
    MoveDirectorMethods,
    ViewerDirectorMethods,
)

discover_string = Request(1, "rpc.discover").model_dump_json()


class Test_MoveDirector_methods:
    @pytest.fixture(scope="class")
    def methods(self) -> list[str]:
        dir_class = DAQ_Move_LECODirector
        dir_class.start_timer = print  # type: ignore
        dir = dir_class()
        response = dir.listener.message_handler.rpc.process_request(discover_string)
        assert response is not None
        result = dir.listener.message_handler.rpc_generator.get_result_from_response(response)
        methods = result["methods"]
        dir.listener.stop_listen()
        return [item["name"] for item in methods]

    @pytest.mark.parametrize("method", GenericDirectorMethods)
    def test_generic_methods_are_present(self, method, methods):
        assert method in methods

    @pytest.mark.parametrize("method", MoveDirectorMethods)
    def test_move_methods_are_present(self, method, methods):
        assert method in methods


class Test_ViewerDirector_methods:
    @pytest.fixture(scope="class")
    def methods(self) -> list[str]:
        dir_class = DAQ_xDViewer_LECODirector
        dir_class.start_timer = print  # type: ignore
        dir = dir_class()
        response = dir.listener.message_handler.rpc.process_request(discover_string)
        assert response is not None
        result = dir.listener.message_handler.rpc_generator.get_result_from_response(response)
        methods = result["methods"]
        return [item["name"] for item in methods]

    @pytest.mark.parametrize("method", GenericDirectorMethods)
    def test_generic_methods_are_present(self, method, methods):
        assert method in methods

    @pytest.mark.parametrize("method", ViewerDirectorMethods)
    def test_move_methods_are_present(self, method, methods):
        assert method in methods

