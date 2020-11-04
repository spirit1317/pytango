

# Imports
from concurrent.futures import Future

import pytest
from numpy.testing import assert_array_equal

import tango

#each datatype requires different TangoTest command
dtype_dict = {
    int: 'DevLong64',
    float: 'DevDouble',
    str: 'DevString',
    bool: 'DevBoolean',
    (int,): 'DevVarLong64Array',
    (float,): 'DevVarDoubleArray',
    (str,): 'DevVarStringArray',
}

def test_async_command_polled(tango_test, typed_values):
    dtype, values, expected = typed_values

    if dtype == (bool,):
        pytest.xfail('Not supported for some reasons')

    proxy = tango_test
    
    command_name = dtype_dict[dtype] 
    
    for value in values:
        eid = proxy.command_inout_asynch(command_name, value)
        result = proxy.command_inout_reply(eid, timeout=500)
        assert_array_equal(result, expected(value))


def test_async_command_with_polled_callback(tango_test, typed_values):
    dtype, values, expected = typed_values

    if dtype == (bool,):
        pytest.xfail('Not supported for some reasons')

    proxy = tango_test
    
    command_name = dtype_dict[dtype]
    
    api_util = tango.ApiUtil.instance()
    api_util.set_asynch_cb_sub_model(tango.cb_sub_model.PULL_CALLBACK)

    for value in values:
        future = Future()
        proxy.command_inout_asynch(command_name, value, future.set_result)
        api_util.get_asynch_replies(500)
        result = future.result()
        assert_array_equal(result.argout, expected(value))


def test_async_command_with_pushed_callback(tango_test, typed_values):
    dtype, values, expected = typed_values

    if dtype == (bool,):
        pytest.xfail('Not supported for some reasons')

    proxy = tango_test
    
    command_name = dtype_dict[dtype]

    api_util = tango.ApiUtil.instance()
    api_util.set_asynch_cb_sub_model(tango.cb_sub_model.PUSH_CALLBACK)

    for value in values:
        future = Future()
        proxy.command_inout_asynch(command_name, value, future.set_result)
        result = future.result(timeout=0.5)
        assert_array_equal(result.argout, expected(value))
