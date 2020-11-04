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
    
    status = '\n'.join((
        "This is a multiline status",
        "with special characters such as",
        "Café à la crème)`'-.,_"))
    
    class TestDevice(Device):
        green_mode = green_mode
        
        #test_set_status
        def init_device(self):
            self.set_state(DevState.ON)
            self.set_status(status)
        
        #test_device_property_with_default_value
        
        prop = device_property(dtype=dtype, default_value=default_prop_val)

        @command(dtype_out=patched_dtype)
        def get_prop(self):
            return self.prop
         
        #test_polled_attribute
            
        @attribute(polling_period=100)
        def PolledAttribute1(self):
            return 42.0

        @attribute(polling_period=100000)
        def PolledAttribute2(self):
            return 43.0

        @attribute(polling_period=500)
        def PolledAttribute3(self):
            return 44.0
        
        #test_read_write_dev_encoded
        
        attr2_value = ("uint8", b"\xd2\xd3")
        
        @attribute(dtype=DevEncoded,
                   access=AttrWriteType.READ_WRITE)
        def attr2(self):
            return self.attr2_value

        @attr2.write
        def attr(self, value):
            self.attr2_value = value

        @command(dtype_in=DevEncoded)
        def cmd_in(self, value):
            self.attr2_value = value

        @command(dtype_out=DevEncoded)
        def cmd_out(self):
            return self.attr2_value

        @command(dtype_in=DevEncoded, dtype_out=DevEncoded)
        def cmd_in_out(self, value):
            self.attr2_value = value
            return self.attr2_value
            
    
    TestDevice.run_server(sys.argv[4:],post_init_callback=post_init_callback)