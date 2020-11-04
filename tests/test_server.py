# -*- coding: utf-8 -*-

import sys
import textwrap
import pytest
import enum
import socket
import os

from tango import DevState, AttrWriteType, GreenMode, DevFailed, DevEncoded
from tango.server import Device
from tango.server import command, attribute, device_property
from tango.test_utils import DeviceTestContext, assert_close, \
    GoodEnum, BadEnumNonZero, BadEnumSkipValues, BadEnumDuplicates
from tango.utils import get_enum_labels, EnumTypeError


# Asyncio imports
try:
    import asyncio
except ImportError:
    import trollius as asyncio  # noqa: F401

# Constants
PY3 = sys.version_info >= (3,)
YIELD_FROM = "yield from" if PY3 else "yield asyncio.From"
RETURN = "return" if PY3 else "raise asyncio.Return"


# Test state/status

def test_set_state(device_test_server_1 ,state):
    proxy = device_test_server_1
    status = 'The device is in {0!s} state.'.format(state)
    
    assert proxy.state() == state
    assert proxy.status() == status


def test_set_status(device_test_server_4):
    proxy = device_test_server_4

    status = '\n'.join((
        "This is a multiline status",
        "with special characters such as",
        "Café à la crème)`'-.,_"))
        
    assert proxy.state() == DevState.ON
    assert proxy.status() == status
    
# Test commands

def test_identity_command(device_test_server_2, typed_values):
    proxy=device_test_server_2
    dtype, values, expected = typed_values

    if dtype == (bool,):
        pytest.xfail('Not supported for some reasons')
        
    for value in values:
        assert_close(proxy.identity(value), expected(value))


def test_polled_command(device_test_server_3,server_green_mode):
    proxy = device_test_server_3

    dct = {'Polling1': 100,
           'Polling2': 100000,
           'Polling3': 500}

    ans = proxy.polling_status()

    for info in ans:
        lines = info.split('\n')
        comm = lines[0].split('= ')[1]
        period = int(lines[1].split('= ')[1])
        assert dct[comm] == period


def test_wrong_command_result(device_test_server_3):
    proxy = device_test_server_3
    
    with pytest.raises(DevFailed):
        proxy.cmd_str_err()
    with pytest.raises(DevFailed):
        proxy.cmd_int_err()
    with pytest.raises(DevFailed):
        proxy.cmd_str_list_err()

# Test attributes
#TODO: why this test fail on strings but not on Linux ?
def test_read_write_attribute(device_test_server_2,typed_values):
    proxy=device_test_server_2
    dtype, values, expected = typed_values
    
    for value in values:
        proxy.attr = value
        #if(dtype == (str,)):
        #    print("proxy.attr")
        #    print(proxy.attr)
        #    print("value:")
        #    print(value)
        assert_close(proxy.attr, expected(value))


def test_read_write_attribute_enum(device_test_server_3,server_green_mode):
    proxy = device_test_server_3
    values = (member.value for member in GoodEnum)
    enum_labels = get_enum_labels(GoodEnum)
    
    for value, label in zip(values, enum_labels):
        proxy.attr_from_enum = value
        read_attr = proxy.attr_from_enum
        assert read_attr == value
        assert isinstance(read_attr, enum.IntEnum)
        assert read_attr.value == value
        assert read_attr.name == label
        proxy.attr_from_labels = value
        read_attr = proxy.attr_from_labels
        assert read_attr == value
        assert isinstance(read_attr, enum.IntEnum)
        assert read_attr.value == value
        assert read_attr.name == label
    for value, label in zip(values, enum_labels):
        proxy.attr_from_enum = label
        read_attr = proxy.attr_from_enum
        assert read_attr == value
        assert isinstance(read_attr, enum.IntEnum)
        assert read_attr.value == value
        assert read_attr.name == label
        proxy.attr_from_labels = label
        read_attr = proxy.attr_from_labels
        assert read_attr == value
        assert isinstance(read_attr, enum.IntEnum)
        assert read_attr.value == value
        assert read_attr.name == label
    
    with pytest.raises(TypeError) as context:
        class BadTestDevice(Device):
            green_mode = server_green_mode

            def __init__(self, *args, **kwargs):
                super(BadTestDevice, self).__init__(*args, **kwargs)
                self.attr_value = 0

            # enum_labels may not be specified if dtype is an enum.Enum
            @attribute(dtype=GoodEnum, enum_labels=enum_labels)
            def bad_attr(self):
                return self.attr_value

        BadTestDevice()  # dummy instance for Codacy
    assert 'enum_labels' in str(context.value)
    

def test_wrong_attribute_read(device_test_server_3):
    proxy = device_test_server_3  
            
    with pytest.raises(DevFailed):
        proxy.attr_str_err
    with pytest.raises(DevFailed):
        proxy.attr_int_err
    with pytest.raises(DevFailed):
        proxy.attr_str_list_err


# Test properties

def test_device_property_no_default(device_test_server_2, typed_values):
    proxy = device_test_server_2
    
    dtype, values, expected = typed_values
    default = values[0]

    assert_close(proxy.get_prop_1(), expected(default))


"""
#TODO: make this work
def test_device_property_with_default_value(device_test_server_2, typed_values):
    proxy = device_test_server_2
    dtype, values, expected = typed_values

    default = values[0]
    
    assert_close(proxy.get_prop_2(), expected(default))
"""

# Test inheritance
"""
#TODO: make this work
def test_inheritance(server_green_mode):

    class A(Device):
        green_mode = server_green_mode

        prop1 = device_property(dtype=str, default_value="hello1")
        prop2 = device_property(dtype=str, default_value="hello2")

        @command(dtype_out=str)
        def get_prop1(self):
            return self.prop1

        @command(dtype_out=str)
        def get_prop2(self):
            return self.prop2

        @attribute(access=AttrWriteType.READ_WRITE)
        def attr_1(self):
            return self.attr_1_value

        @attr.write
        def attr_1(self, value):
            self.attr_1_value = value

        def dev_status(self):
            return ")`'-.,_"

    class B(A):

        prop2 = device_property(dtype=str, default_value="goodbye2")

        @attribute
        def attr2(self):
            return 3.14

        def dev_status(self):
            return 3 * A.dev_status(self)

        if server_green_mode == GreenMode.Asyncio:
            code = textwrap.dedent(""""""\
                @asyncio.coroutine
                def dev_status(self):
                    coro = super(type(self), self).dev_status()
                    result = {YIELD_FROM}(coro)
                    {RETURN}(3*result)
            """""").format(**globals())
            exec(code)

    with DeviceTestContext(B) as proxy:
        assert proxy.get_prop1() == "hello1"
        assert proxy.get_prop2() == "goodbye2"
        proxy.attr = 1.23
        assert proxy.attr == 1.23
        assert proxy.attr2 == 3.14
        assert proxy.status() == ")`'-.,_)`'-.,_)`'-.,_"
"""

def test_polled_attribute(device_test_server_4):
    proxy = device_test_server_4

    dct = {'PolledAttribute1': 100,
           'PolledAttribute2': 100000,
           'PolledAttribute3': 500}

    ans = proxy.polling_status()
    #print(f"polling status:{ans}")
    
    for x in ans:
        lines = x.split('\n')
        attr = lines[0].split('= ')[1]
        poll_period = int(lines[1].split('= ')[1])
        assert dct[attr] == poll_period

"""
#TODO: make this run
def test_mandatory_device_property(typed_values, server_green_mode):
    dtype, values, expected = typed_values
    patched_dtype = dtype if dtype != (bool,) else (int,)
    default, value = values[:2]

    class TestDevice(Device):
        green_mode = server_green_mode

        prop = device_property(dtype=dtype, mandatory=True)

        @command(dtype_out=patched_dtype)
        def get_prop(self):
            return self.prop
    
    with DeviceTestContext(TestDevice,
                           properties={'prop': value},
                           process=True) as proxy:
        assert_close(proxy.get_prop(), expected(value))
    
    with pytest.raises(DevFailed) as context:
        with DeviceTestContext(TestDevice, process=True) as proxy:
            pass
    assert 'Device property prop is mandatory' in str(context.value)
"""

# fixtures

@pytest.fixture(params=[GoodEnum])
def good_enum(request):
    return request.param


@pytest.fixture(params=[BadEnumNonZero, BadEnumSkipValues, BadEnumDuplicates])
def bad_enum(request):
    return request.param


# test utilities for servers

def test_get_enum_labels_success(good_enum):
    expected_labels = ['START', 'MIDDLE', 'END']
    assert get_enum_labels(good_enum) == expected_labels


def test_get_enum_labels_fail(bad_enum):
    with pytest.raises(EnumTypeError):
        get_enum_labels(bad_enum)


# DevEncoded

def test_read_write_dev_encoded(device_test_server_4):
    proxy = device_test_server_4
    
    assert proxy.attr2 == ("uint8", b"\xd2\xd3")

    proxy.attr2 = ("uint8", b"\xde")
    assert proxy.attr2 == ("uint8", b"\xde")

    proxy.cmd_in(("uint8", b"\xd4\xd5"))
    assert proxy.cmd_out() == ("uint8", b"\xd4\xd5")

    proxy.cmd_in_out(('uint8', b"\xd6\xd7"))
    assert proxy.attr2 == ("uint8", b"\xd6\xd7")

# Test Exception propagation

def test_exeption_propagation(device_test_server_3):
    proxy = device_test_server_3

    with pytest.raises(DevFailed) as record:
        proxy.attr_err  # pylint: disable=pointless-statement
    assert "ZeroDivisionError" in record.value.args[0].desc

    with pytest.raises(DevFailed) as record:
        proxy.cmd_err()
    assert "ZeroDivisionError" in record.value.args[0].desc
