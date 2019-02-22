"""Specialised input handler for the hestia project
"""

from __future__ import absolute_import

import re
from .. import config
import pynbody
from .pynbody import PynbodyInputHandler
from . import halo_stat_files
import os.path
import weakref

_loaded_halocats = {}

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
            tmp_path = ahf_path + '/HESTIA_*%.3d.z*AHF_halos' % snap_id
            cat = glob.glob(tmp_path)[0]
            return cat[:-5]
        else:
            raise IOError("Cannot infer path of halos")
    
    def _extension_to_filename(self, ts_extension):
        return str(os.path.join(config.base, self.basename, self._pynbody_path_from_snapdir_path(ts_extension)))

    def _is_able_to_load(self, filepath):
        try:
            f = pynbody.load(self._pynbody_path_from_snapdir_path(filepath))
            h = pynbody.halo.AHFCatalogue(f, ahf_basename=self._AHF_path_from_snapdir_path(filepath))
            return True
        except (IOError, RuntimeError):
            return False

    def _construct_halo_cat(self, ts_extension, object_typetag):
        if object_typetag!= 'halo':
            raise ValueError("Unknown object type %r" % object_typetag)
        f = self.load_timestep(ts_extension)
        h = _loaded_halocats.get(id(f), lambda: None)()
        if h is None:
            tmp_path = os.path.join(config.base, self.basename, ts_extension)
            h = pynbody.halo.AHFCatalogue(f, ahf_basename=self._AHF_path_from_snapdir_path(tmp_path))
            _loaded_halocats[id(f)] = weakref.ref(h)
            f._db_current_halocat = h # keep alive for lifetime of simulation
        return h  # pynbody.halo.AmigaGrpCatalogue(f)

    def match_objects(self, ts1, ts2, halo_min, halo_max,
                      dm_only=True, threshold=0.005, object_typetag='halo',
                      output_handler_for_ts2=None):
        return super(HestiaInputHandler, self).match_objects(ts1, ts2, halo_min, halo_max, dm_only, threshold, object_typetag, output_handler_for_ts2)


class HestiaAHFStatFile(halo_stat_files.AHFStatFile):

    @classmethod
    def filename(cls, timestep_filename):
        import glob
        file_list = glob.glob(HestiaInputHandler._AHF_path_from_snapdir_path(os.path.split(timestep_filename)[0])+'halos')

        # permit the AHF halos to be in a subfolder called "halos", for yt purposes
        # (where the yt tipsy reader can't cope with the AHF files being in the same folder)
        parts = timestep_filename.split("/")
        parts_with_halo = parts[:-1]+["halos"]+parts[-1:]
        filename_with_halo = "/".join(parts_with_halo)
        file_list+=glob.glob(filename_with_halo+'.z*.???.AHF_halos')

        if len(file_list)==0:
            return "CannotFindAHFHaloFilename"
        else:
            return file_list[0]

