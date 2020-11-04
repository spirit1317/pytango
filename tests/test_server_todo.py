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

#TODO: make this run
def test_device_property_with_default_value(device_test_server_5, typed_values):
    proxy = device_test_server_5
    dtype, values, expected = typed_values

    default = values[0]
    
    assert_close(proxy.get_prop(), expected(default))

# Test inheritance
"""
#TODO: make this run
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
     
    with pytest.raises(DevFailed) as context:
        TestDevice.run_server(["instance_1","-ORBendPoint","giop:tcp:10.0.2.15:58206","-nodb","-dlist","test_device/event_device/1"])
    assert 'Device property prop is mandatory' in str(context.value)
    
    
    with DeviceTestContext(TestDevice,
                           properties={'prop': value},
                           process=True) as proxy:
        assert_close(proxy.get_prop(), expected(value))
    
    with pytest.raises(DevFailed) as context:
        with DeviceTestContext(TestDevice, process=True) as proxy:
            pass
    assert 'Device property prop is mandatory' in str(context.value)
"""
