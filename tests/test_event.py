# Imports

import time
import socket
from functools import partial

import pytest
from six import StringIO

from tango import EventType, GreenMode, DeviceProxy, AttrQuality
from tango.server import Device
from tango.server import command, attribute
from tango.test_utils import DeviceTestContext
from tango.utils import EventCallback

from tango.gevent import DeviceProxy as gevent_DeviceProxy
from tango.futures import DeviceProxy as futures_DeviceProxy
from tango.asyncio import DeviceProxy as asyncio_DeviceProxy


# Tests
def test_subscribe_change_event(event_device):
    results = []

    def callback(evt):
        results.append(evt.attr_value.value)

    # Subscribe
    eid = event_device.subscribe_event(
        "attr", EventType.CHANGE_EVENT, callback, wait=True)
    #TODO: find out how to uncomment this line without an error
    #assert eid == 1
    # Trigger an event
    event_device.command_inout("send_event", wait=True)
    # Wait for tango event
    retries = 20
    for _ in range(retries):
        event_device.read_attribute("state", wait=True)
        if len(results) > 1:
            break
        time.sleep(0.05)
    # Test the event values
    assert results == [0., 1.]
    # Unsubscribe
    event_device.unsubscribe_event(eid)


def test_subscribe_interface_event(event_device):
    results = []

    def callback(evt):
        results.append(evt)

    # Subscribe
    eid = event_device.subscribe_event(
        "attr", EventType.INTERFACE_CHANGE_EVENT, callback, wait=True)
    #assert eid == 1
    # Trigger an event
    event_device.command_inout("add_dyn_attr", 'bla', wait=True)
    event_device.read_attribute('bla', wait=True) == 1.23
    # Wait for tango event
    retries = 30
    for _ in range(retries):
        event_device.read_attribute("state", wait=True)
        if len(results) > 1:
            break
        time.sleep(0.05)
    event_device.command_inout("delete_dyn_attr", 'bla', wait=True)
    # Wait for tango event
    retries = 30
    for _ in range(retries):
        event_device.read_attribute("state", wait=True)
        if len(results) > 2:
            break
        time.sleep(0.05)
    # Test the first event value
    assert set(cmd.cmd_name for cmd in results[0].cmd_list) == \
        {'Init', 'State', 'Status',
         'add_dyn_attr', 'delete_dyn_attr',
         'send_event', 'send_event_with_timestamp'}
    assert set(att.name for att in results[0].att_list) == \
        {'attr', 'State', 'Status'}
    # Test the second event value
    assert set(cmd.cmd_name for cmd in results[1].cmd_list) == \
        {'Init', 'State', 'Status',
         'add_dyn_attr', 'delete_dyn_attr',
         'send_event', 'send_event_with_timestamp'}
    assert set(att.name for att in results[1].att_list) == \
        {'attr', 'State', 'Status', 'bla'}
    # Test the third event value
    assert set(cmd.cmd_name for cmd in results[2].cmd_list) == \
        {'Init', 'State', 'Status',
         'add_dyn_attr', 'delete_dyn_attr',
         'send_event', 'send_event_with_timestamp'}
    assert set(att.name for att in results[2].att_list) == \
        {'attr', 'State', 'Status'}
    # Unsubscribe
    event_device.unsubscribe_event(eid)


def test_push_event_with_timestamp(event_device):
    string = StringIO()
    ec = EventCallback(fd=string)
    # Subscribe
    eid = event_device.subscribe_event(
        "attr", EventType.CHANGE_EVENT, ec, wait=True)
    #assert eid == 1
    # Trigger an event
    event_device.command_inout("send_event_with_timestamp", wait=True)
    # Wait for tango event
    retries = 20
    for _ in range(retries):
        event_device.read_attribute("state", wait=True)
        if len(ec.get_events()) > 1:
            break
        time.sleep(0.05)
    # Test the event values and timestamp
    results = [evt.attr_value.value for evt in ec.get_events()]
    assert results == [0., 2.]
    assert ec.get_events()[-1].attr_value.time.totime() == 3.
    # Check string
    line1 = "TEST_DEVICE/EVENT_DEVICE/1 ATTR#DBASE=NO CHANGE [ATTR_VALID] 0.0"
    line2 = "TEST_DEVICE/EVENT_DEVICE/1 ATTR#DBASE=NO CHANGE [ATTR_WARNING] 2.0"
    assert line1 in string.getvalue()
    assert line2 in string.getvalue()
    # Unsubscribe
    event_device.unsubscribe_event(eid)