"""Specialised input handler for the hestia project
http://www.caterpillarproject.org"""

from __future__ import absolute_import

import re
from .. import config
from .pynbody import PynbodyInputHandler
from . import halo_stat_files
import os.path

class HestiaInputHandler(PynbodyInputHandler):
    patterns = ["snapdir_???","snapshot_???"]

    @classmethod
    def _snap_id_from_snapdir_path(cls, path):
        match = re.match(".*snapdir_([0-9]{3})/?", path)
        if match:
            return int(match.group(1))
        else:
            return None

    @classmethod
    def _pynbody_path_from_snapdir_path(cls, path):
        snap_id = cls._snap_id_from_snapdir_path(path)
        if snap_id is not None:
            return os.path.join(path, "snapshot_%.3d" % snap_id)
        else:
            raise IOError("Cannot infer correct path to pass to pynbody")

    @classmethod
    def _AHF_path_from_snapdir_path(cls, path):
        snap_id = cls._snap_id_from_snapdir_path(path)
        if snap_id is not None:
            import glob
            ahf_path = os.path.join(os.path.split(os.path.split(path)[0])[0],"AHF_output")
            tmp_path = ahf_path + '/HESTIA_100Mpc_*.%.3d.z*_halos' % snap_id
            cat = glob.glob(tmp_path)[0]
            return cat[:-5]
        else:
            raise IOError("Cannot infer path of halos")

    def _extension_to_filename(self, ts_extension):
        return str(os.path.join(config.base, self.basename, self._pynbody_path_from_snapdir_path(ts_extension)))

    def _is_able_to_load(self, filepath):
        #try:
        import pynbody
        f = pynbody.load(self._pynbody_path_from_snapdir_path(filepath))
        h = pynbody.halo.AHFCatalogue(f, ahf_basename=self._AHF_path_from_snapdir_path(filepath))
        return True
        #except (IOError, RuntimeError):
        #    return False


