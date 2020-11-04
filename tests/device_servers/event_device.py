"""Demo power supply tango device server"""
import time
import numpy
import sys
import os

from tango import AttrQuality, AttrWriteType, DispLevel, DevState, DebugIt
from tango.server import Device, attribute, command, pipe, device_property



def print_err(s):
    sys.stderr.write(s)
    sys.stderr.flush()


class EventDevice(Device):

    def init_device(self):
        self.set_change_event("attr", True, False)

    @attribute
    def attr(self):
        return 0.
    """
    @command
    def say_hello(self):
        msg = f"Hello, my pid:{os.getpid()}"
        with open(os.path.dirname(__file__)+'/event_device.log',"a") as f:
            f.write(msg)
        print(msg)
    """
    @command
    def send_event(self):
        self.push_change_event("attr", 1.)

    @command
    def send_event_with_timestamp(self):
        self.push_change_event("attr", 2., 3., AttrQuality.ATTR_WARNING)

    @command(dtype_in=str)
    def add_dyn_attr(self, name):
        attr = attribute(
            name=name,
            dtype='float',
            fget=self.read)
        self.add_attribute(attr)

    @command(dtype_in=str)
    def delete_dyn_attr(self, name):
        self._remove_attribute(name)

    def read(self, attr):
        attr.set_value(1.23)


def post_init_callback():
    """Have to print the ready message for xprocess"""
    print_err('Ready to accept request')
   
 
if __name__ == "__main__":
    EventDevice.run_server(post_init_callback=post_init_callback)