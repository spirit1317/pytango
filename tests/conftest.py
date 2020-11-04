"""Load tango-specific pytest fixtures."""

from tango.test_utils import state, typed_values, server_green_mode

#new imports
from distutils.spawn import find_executable
from subprocess import Popen
import platform
from time import sleep

import psutil
import pytest
import time
import socket
from functools import partial
import sys
import os
import tempfile

from xprocess import ProcessStarter
from functools import partial
from tango import DeviceProxy, DevFailed, GreenMode
from tango import DeviceInfo, AttributeInfo, AttributeInfoEx
from tango.utils import is_str_type, is_int_type, is_float_type, is_bool_type
from tango.test_utils import PY3, assert_close, bytes_devstring, str_devstring

from tango.gevent import DeviceProxy as gevent_DeviceProxy
from tango.futures import DeviceProxy as futures_DeviceProxy
from tango.asyncio import DeviceProxy as asyncio_DeviceProxy

__all__ = ('state', 'typed_values', 'server_green_mode')

device_proxy_map = {
    GreenMode.Synchronous: DeviceProxy,
    GreenMode.Futures: futures_DeviceProxy,
    GreenMode.Asyncio: partial(asyncio_DeviceProxy, wait=True),
    GreenMode.Gevent: gevent_DeviceProxy}


# Helpers

def get_open_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port
    

def find_process_id(processName):
    processes = []
    for process in psutil.process_iter():
        try:
            process_info = process.as_dict(attrs=['pid', 'name'])
            if processName.lower() in process_info['name'].lower():
                processes.append(process_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return processes


def get_ports(pid):
    p = psutil.Process(pid)
    conns = p.connections(kind="tcp")
    # Sorting by family in order to make any IPv6 address go first.
    # Otherwise there's a 50% chance that the proxy will just
    # hang (presumably because it's connecting on the wrong port)
    # This works on my machine, not sure if it's a general
    # solution though.
    conns = reversed(sorted(conns, key=lambda c: c.family))
    return [c.laddr[1] for c in conns]


def start_server(server, inst, device):
    exe = find_executable(server)
    cmd = ("{0} {1} -ORBendPoint giop:tcp::0 -nodb -dlist {2}"
           .format(exe, inst, device))
    proc = Popen(cmd.split(), close_fds=True)
    proc.poll()
    return proc


def get_proxy(host, port, device, green_mode):
    access = "tango://{0}:{1}/{2}#dbase=no".format(
        host, port, device)
    return device_proxy_map[green_mode](access)


def wait_for_proxy(host, pid, device, green_mode, retries=10, delay=0.01):
    for i in range(retries):
        ports = get_ports(pid)
        if ports:
            try:
                proxy = get_proxy(host, ports[0], device, green_mode)
                proxy.ping()
                proxy.state()
                return proxy
            except DevFailed:
                pass
        sleep(delay)
    else:
        raise RuntimeError("TangoTest device did not start up!")


# Fixtures
@pytest.fixture(params=[GreenMode.Synchronous,
                        GreenMode.Asyncio,
                        GreenMode.Gevent],
                scope="session",
                autouse=True)
def tango_test(xprocess, request):
    # python_executable_full_path = sys.executable
    # python_server_script_full_path = py.path.local(__file__).dirpath("echo_server.py")
    green_mode = request.param
    server = "TangoTest"
    inst = "test"
    device = "sys/tg_test/17"
    host = platform.node()
    exe = find_executable(server)

    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [exe, inst, "-ORBendPoint", "giop:tcp::0", "-nodb", "-dlist", device]
    info = xprocess.ensure("tango_test_server", Starter)
    pid = info[0]
    pid = find_process_id("TangoTest")[0]["pid"]
    proxy = wait_for_proxy(host, pid, device, green_mode)
    yield proxy
    xprocess.getinfo("tango_test_server").terminate()
    

@pytest.fixture(params=[GreenMode.Synchronous,
                        GreenMode.Futures,
                        GreenMode.Asyncio,
                        GreenMode.Gevent],
                scope="module")
def event_device(xprocess,request):
    green_mode = request.param
    # Hack: a port have to be specified explicitely for events to work
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/event_device.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    db_content = "EventDevice/instance_1/DEVICE/EventDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [python_path, device_path, "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
        
    info = xprocess.ensure("tango_event_device", Starter)
    access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    proxy = device_proxy_map[green_mode](access)
    #proxy.command_inout('say_hello')
    yield proxy
    
    xprocess.getinfo("tango_event_device").terminate()
    os.close(handle)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def device_test_server_1(xprocess,server_green_mode,state):
    # Hack: a port have to be specified explicitely for events to work
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/device_test_server_1.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    device_access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    db_content = "TestDevice/instance_1/DEVICE/TestDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [sys.executable, device_path, str(server_green_mode), str(state), "_", "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
    
    info = xprocess.ensure("tango_test_device", Starter)
    #for some reason only this proxy is used, as in DeviceContext
    proxy = DeviceProxy(device_access)
    
    yield proxy
    
    xprocess.getinfo("tango_test_device").terminate()
    os.close(handle)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def device_test_server_2(xprocess,server_green_mode,typed_values):
    # Hack: a port have to be specified explicitely for events to work
    dtype, _, _ = typed_values
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/device_test_server_1.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    device_access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    db_content = "TestDevice/instance_1/DEVICE/TestDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [sys.executable, device_path, str(server_green_mode), "_", str(dtype), "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
    
    info = xprocess.ensure("tango_test_device", Starter)
    #for some reason only this proxy is used, as in DeviceContext
    proxy = DeviceProxy(device_access)
    
    yield proxy
    
    xprocess.getinfo("tango_test_device").terminate()
    os.close(handle)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def device_test_server_3(xprocess,server_green_mode):
    # Hack: a port have to be specified explicitely for events to work
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/device_test_server_1.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    device_access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    db_content = "TestDevice/instance_1/DEVICE/TestDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [sys.executable, device_path, str(server_green_mode), "_", "_", "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
    
    info = xprocess.ensure("tango_test_device", Starter)
    #for some reason only this proxy is used, as in DeviceContext
    proxy = DeviceProxy(device_access)
    
    yield proxy
    
    xprocess.getinfo("tango_test_device").terminate()
    os.close(handle)
    os.unlink(db_path)


@pytest.fixture(scope="function")
def device_test_server_4(xprocess,server_green_mode):
    # Hack: a port have to be specified explicitely for events to work
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/device_test_server_2.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    device_access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    db_content = "TestDevice/instance_1/DEVICE/TestDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [sys.executable, device_path, str(server_green_mode), "_", "_", "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
    
    info = xprocess.ensure("tango_test_device", Starter)
    #for some reason only this proxy is used, as in DeviceContext
    proxy = DeviceProxy(device_access)
    
    yield proxy
    
    xprocess.getinfo("tango_test_device").terminate()
    os.close(handle)
    os.unlink(db_path)
    
    
@pytest.fixture(scope="function")
def device_test_server_5(xprocess,server_green_mode,typed_values):
    # Hack: a port have to be specified explicitely for events to work
    dtype, _, _ = typed_values
    python_path = sys.executable
    device_path = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'device_servers/device_test_server_2.py'))
    host = socket.gethostbyname(socket.gethostname())#'localhost'#platform.node()
    port = get_open_port()
    
    handle, db_path = tempfile.mkstemp()
    device = 'test_device/event_device/1'
    device_access = "tango://{0}:{1}/{2}#dbase=no".format(host,port,device)
    db_content = "TestDevice/instance_1/DEVICE/TestDevice: \"{0}\"\n".format(device)
    
    with open(db_path,'w') as f:
        f.write(db_content)
    
    class Starter(ProcessStarter):
        pattern = 'Ready to accept request'
        args = [sys.executable, device_path, str(server_green_mode), "_", str(dtype), "instance_1", "-ORBendPoint", "giop:tcp:{0}:{1}".format(host,port), "-file={0}".format(db_path) ]
    
    info = xprocess.ensure("tango_test_device", Starter)
    #for some reason only this proxy is used, as in DeviceContext
    proxy = DeviceProxy(device_access)
    
    yield proxy
    
    xprocess.getinfo("tango_test_device").terminate()
    os.close(handle)
    os.unlink(db_path)