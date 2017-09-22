from __future__ import absolute_import
from __future__ import print_function
import tangos.parallel_tasks.pynbody_server as ps
import tangos.parallel_tasks as pt
import tangos
import numpy.testing as npt
import pynbody
import sys
import os
from six.moves import zip

def setup():
    pt.use("multiprocessing")
    tangos.config.base = os.path.dirname(__file__)+"/"

def _get_array():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    for fname in pt.distributed(["test_simulations/test_tipsy/tiny.000640", "test_simulations/test_tipsy/tiny.000832"]):
        ps.RequestLoadPynbodySnapshot(tangos.config.base+fname).send(0)
        ps.ConfirmLoadPynbodySnapshot.receive(0)

        ps.RequestPynbodyArray(test_filter, "pos").send(0)

        f_local = pynbody.load(tangos.config.base+fname)
        f_local.physical_units()
        remote_result =  ps.ReturnPynbodyArray.receive(0).contents
        assert (f_local[test_filter]['pos']==remote_result).all()

        ps.ReleasePynbodySnapshot().send(0)


def test_get_array():
    pt.launch(_get_array,3)


def _test_simsnap_properties():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    f_local = pynbody.load(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")[test_filter]
    f_local.physical_units()

    assert len(f)==len(f_local)
    assert len(f.dm)==len(f_local.dm)
    assert len(f.gas)==len(f_local.gas)
    assert len(f.star)==len(f_local.star)
    assert f.properties['boxsize']==f_local.properties['boxsize']


def test_simsnap_properties():
    pt.launch(_test_simsnap_properties,2)


def _test_simsnap_arrays():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    f_local = pynbody.load(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")[test_filter]
    f_local.physical_units()
    assert (f['x'] == f_local['x']).all()
    assert (f.gas['iord'] == f_local.gas['iord']).all()

def test_simsnap_arrays():
    pt.launch(_test_simsnap_arrays,2)

def _test_nonexistent_array():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    with npt.assert_raises(KeyError):
        f['nonexistent']

def test_nonexistent_array():
    pt.launch(_test_nonexistent_array, 2)


def _test_halo_array():
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(1)
    f_local = pynbody.load(tangos.config.base+"test_simulations/test_tipsy/tiny.000640").halos()[1]
    assert len(f)==len(f_local)
    assert (f['x'] == f_local['x']).all()
    assert (f.gas['temp'] == f_local.gas['temp']).all()

def test_halo_array():
    pt.launch(_test_halo_array, 2)


def _test_remote_file_index():
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(1)
    f_local = pynbody.load(tangos.config.base+"test_simulations/test_tipsy/tiny.000640").halos()[1]
    local_index_list = f_local.get_index_list(f_local.ancestor)
    index_list = f['remote-index-list']
    assert (index_list==local_index_list).all()

def test_remote_file_index():
    pt.launch(_test_remote_file_index, 2)

def _debug_print_arrays(*arrays):
    for vals in zip(*arrays):
        print(vals, file=sys.stderr)

def _test_lazy_evaluation_is_local():
    conn = ps.RemoteSnapshotConnection(tangos.config.base+"test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(1)
    f_local = pynbody.load(tangos.config.base+"test_simulations/test_tipsy/tiny.000640").halos()[1]
    f_local.physical_units()

    centre_offset = (-6017.0,-123.8,566.4)
    f['pos']-=centre_offset
    f_local['pos']-=centre_offset

    npt.assert_almost_equal(f['x'], f_local['x'])

    # This is the critical test: if the lazy-evaluation of 'r' takes place on the server, it will not be using
    # the updated version of the position array. This is undesirable for two reasons: first, because the pynbody
    # snapshot seen by the client is inconsistent in a way that would never happen with a normal snapshot. Second,
    # because it means extra "derived" arrays are being calculated across the entire snapshot which we want to
    # avoid in a memory-bound situation.
    npt.assert_almost_equal(f['r'], f_local['r'])

def test_lazy_evaluation_is_local():
    pt.launch(_test_lazy_evaluation_is_local, 2)

