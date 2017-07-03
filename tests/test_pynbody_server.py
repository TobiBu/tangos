import tangos.parallel_tasks.pynbody_server as ps
import tangos.parallel_tasks as pt
import numpy.testing as npt
import pynbody
import sys

def setup():
    pt.use("multiprocessing")

def _get_array():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    for fname in pt.distributed(["test_simulations/test_tipsy/tiny.000640", "test_simulations/test_tipsy/tiny.000832"]):
        ps.RequestLoadPynbodySnapshot(fname).send(0)
        ps.ConfirmLoadPynbodySnapshot.receive(0)

        ps.RequestPynbodyArray(test_filter, "x").send(0)

        f_local = pynbody.load(fname)
        f_local.physical_units()
        remote_result =  ps.ReturnPynbodyArray.receive(0).contents
        assert (f_local[test_filter]['x']==remote_result).all()

        ps.ReleasePynbodySnapshot().send(0)


def test_get_array():
    pt.launch(_get_array,3)


def _test_simsnap_properties():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    conn = ps.RemoteSnapshotConnection("test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    f_local = pynbody.load("test_simulations/test_tipsy/tiny.000640")[test_filter]
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
    conn = ps.RemoteSnapshotConnection("test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    f_local = pynbody.load("test_simulations/test_tipsy/tiny.000640")[test_filter]
    f_local.physical_units()
    assert (f['x'] == f_local['x']).all()
    assert (f.gas['iord'] == f_local.gas['iord']).all()

def test_simsnap_arrays():
    pt.launch(_test_simsnap_arrays,2)

def _test_nonexistent_array():
    test_filter = pynbody.filt.Sphere('5000 kpc')
    conn = ps.RemoteSnapshotConnection("test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(test_filter)
    with npt.assert_raises(KeyError):
        f['nonexistent']

def test_nonexistent_array():
    pt.launch(_test_nonexistent_array, 2)


def _test_halo_array():
    conn = ps.RemoteSnapshotConnection("test_simulations/test_tipsy/tiny.000640")
    f = conn.get_view(1)
    f_local = pynbody.load("test_simulations/test_tipsy/tiny.000640").halos()[1]


    assert len(f)==len(f_local)

def test_halo_array():
    pt.launch(_test_halo_array, 2)