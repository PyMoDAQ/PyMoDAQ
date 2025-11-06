import pytest

from pymodaq_utils.serialize import utils


class TestStaticClassMethods:

    def test_int_to_bytes(self):

        afloat = 45.7
        a_negative_integer = -56
        for int_obj in [6, 678900786]:
            bytes_string = utils.int_to_bytes(int_obj)
            assert len(bytes_string) == 4
            assert bytes_string == int_obj.to_bytes(4, 'big')

            assert utils.bytes_to_int(bytes_string) == int_obj

        with pytest.raises(TypeError):
            utils.int_to_bytes(afloat)
        with pytest.raises(ValueError):
            utils.int_to_bytes(a_negative_integer)

    def test_str_to_bytes(self):
        MESSAGE = 'Hello World'
        bytes_message = utils.str_to_bytes(MESSAGE)
        assert bytes_message == MESSAGE.encode()
        assert utils.bytes_to_string(bytes_message) == MESSAGE
        with pytest.raises(TypeError):
            utils.str_to_bytes(56)
        with pytest.raises(TypeError):
            utils.str_to_bytes(56,8)

    def test_str_len_to_bytes(self):

        MESSAGE = 'Hello World'
        bytes_string, bytes_length = utils.str_len_to_bytes(MESSAGE)

        assert bytes_string == MESSAGE.encode()
        assert bytes_length == utils.int_to_bytes(len(MESSAGE))

        assert utils.bytes_to_string(bytes_string) == MESSAGE
