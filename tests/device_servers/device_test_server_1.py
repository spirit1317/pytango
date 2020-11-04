"""Demo power supply tango device server"""
import time
import numpy
import sys
import os

from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt, DevEncoded
from tango.server import Device, attribute, command, pipe, device_property
from tango.test_utils import DeviceTestContext, assert_close, \
    GoodEnum, BadEnumNonZero, BadEnumSkipValues, BadEnumDuplicates, TYPED_VALUES

from tango.utils import get_enum_labels, EnumTypeError

from tango import GreenMode

def print_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()


def post_init_callback():
    """Have to print the ready message for xprocess"""
    print_err('Ready to accept request')
   
   
green_mode_map = {
    str(GreenMode.Synchronous): GreenMode.Synchronous,
    str(GreenMode.Futures): GreenMode.Futures,
    str(GreenMode.Asyncio): GreenMode.Asyncio,
    str(GreenMode.Gevent): GreenMode.Gevent,
}

state_map = {}
for state in DevState.values.values():
    state_map[str(state)] = state

dtype_map = {}
for dtype in TYPED_VALUES:
    dtype_map[str(dtype)] = dtype

enum_labels = get_enum_labels(GoodEnum)

if __name__ == "__main__":
    """program creates a device and runs the test device server with provided green_mode, state, dtype (as first 3 args)
        example:
            python device_test_server.py Gevent UNKNOWN "<class 'float'>" instance_1 -ORBendPoint giop:tcp:10.0.2.15:58206 -file=C:/tmp_db.txt
        use _ for default value:
            python device_test_server.py Gevent _ "<class 'float'>" instance_1 -ORBendPoint giop:tcp:10.0.2.15:58206 -file=C:/tmp_db.txt
    """
    green_mode = green_mode_map[sys.argv[1]] if sys.argv[1] != '_' else GreenMode.Synchronous
    state = state_map[sys.argv[2]] if sys.argv[2] != '_' else state_map["ON"]
    dtype = dtype_map[sys.argv[3]] if sys.argv[3] != '_' else int
    patched_dtype = dtype if dtype != (bool,) else (int,)
    
    default_prop_val = TYPED_VALUES[dtype][0]
    
    class TestDevice(Device):
        green_mode = green_mode
        
        def __init__(self, *args, **kwargs):
            super(TestDevice, self).__init__(*args, **kwargs)
            self.attr_from_enum_value = 0
            self.attr_from_labels_value = 0
        
        #test_set_state
        
        def init_device(self):
            self.set_state(state)
            
        #test_identity_command
            
        @command(dtype_in=dtype, dtype_out=dtype)
        def identity(self, arg):
            return arg
        
        #test_polled_command
        
        @command(polling_period=100)
        def Polling1(self):
            pass

        @command(polling_period=100000)
        def Polling2(self):
            pass

        @command(polling_period=500)
        def Polling3(self):
            pass
        
        #test_wrong_command_result
        
        @command(dtype_out=str)
        def cmd_str_err(self):
            return 1.2345

        @command(dtype_out=int)
        def cmd_int_err(self):
            return "bla"

        @command(dtype_out=[str])
        def cmd_str_list_err(self):
            return ['hello', 55]
            
        #test_read_write_attribute
        
        @attribute(dtype=dtype, max_dim_x=10,
                   access=AttrWriteType.READ_WRITE)
        def attr(self):
            return self.attr_value

        @attr.write
        def attr(self, value):
            self.attr_value = value
            
        #test_read_write_attribute_enum
        
        @attribute(dtype=GoodEnum, access=AttrWriteType.READ_WRITE)
        def attr_from_enum(self):
            return self.attr_from_enum_value

        @attr_from_enum.write
        def attr_from_enum(self, value):
            self.attr_from_enum_value = value

        @attribute(dtype='DevEnum', enum_labels=enum_labels,
                   access=AttrWriteType.READ_WRITE)
        def attr_from_labels(self):
            return self.attr_from_labels_value

        @attr_from_labels.write
        def attr_from_labels(self, value):
            self.attr_from_labels_value = value
            
        #test_wrong_attribute_read
        
        @attribute(dtype=str)
        def attr_str_err(self):
            return 1.2345

        @attribute(dtype=int)
        def attr_int_err(self):
            return "bla"

        @attribute(dtype=[str])
        def attr_str_list_err(self):
            return ['hello', 55]
            
        #test_device_property_no_default
        
        prop_1 = device_property(dtype=dtype)

        @command(dtype_out=patched_dtype)
        def get_prop_1(self):
            return default_prop_val if self.prop_1 is None else self.prop_1
        
        #test_device_property_with_default_value
        
        prop_2 = device_property(dtype=dtype, default_value=default_prop_val)

        @command(dtype_out=patched_dtype)
        def get_prop_2(self):
            return self.prop_2   
        
        #test_exeption_propagation
        
        @attribute
        def attr_err(self):
            1 / 0  # pylint: disable=pointless-statement

        @command
        def cmd_err(self):
            1 / 0  # pylint: disable=pointless-statement
    
    TestDevice.run_server(sys.argv[4:],post_init_callback=post_init_callback)