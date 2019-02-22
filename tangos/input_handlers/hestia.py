"""Specialised input handler for the hestia project"""

from __future__ import absolute_import
from __future__ import print_function

import re
from .. import config
import pynbody
from .pynbody import PynbodyInputHandler
from . import halo_stat_files
import os.path
import weakref
import numpy as np
from six.moves import xrange
from ..log import logger

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
        #try:
        f = pynbody.load(self._pynbody_path_from_snapdir_path(filepath))
        h = pynbody.halo.AHFCatalogue(f, ahf_basename=self._AHF_path_from_snapdir_path(filepath))
        return True
        #except (IOError, RuntimeError):
        #    return False

    def _construct_halo_cat(self, ts_extension, object_typetag):
        if object_typetag!= 'halo':
            raise ValueError("Unknown object type %r" % object_typetag)
        f = self.load_timestep(self._pynbody_path_from_snapdir_path(ts_extension))
        h = _loaded_halocats.get(id(f), lambda: None)()
        if h is None:
            tmp_path = os.path.join(config.base, self.basename, ts_extension)
            h = pynbody.halo.AHFCatalogue(f, ahf_basename=self._AHF_path_from_snapdir_path(tmp_path))
            _loaded_halocats[id(f)] = weakref.ref(h)
            f._db_current_halocat = h # keep alive for lifetime of simulation
        return h  # pynbody.halo.AmigaGrpCatalogue(f)


class HestiaAHFStatFile(halo_stat_files.AHFStatFile):

    @classmethod
    def filename(cls, timestep_filename):
        import glob
        print(HestiaInputHandler._AHF_path_from_snapdir_path(timestep_filename))
        file_list = glob.glob(HestiaInputHandler._AHF_path_from_snapdir_path(timestep_filename))

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



class AHFTree(object):
    def __init__(self, ts):
        self._path = self._AHF_path_from_snapdir_path(ts.extension)
        self._load_raw_links()
        self._load_Mvir(ts.prev)

    def _AHF_path_from_snapdir_path(cls, path):
        snap_id = cls._snap_id_from_snapdir_path(path)
        if snap_id is not None:
            import glob
            ahf_path = os.path.join(os.path.split(os.path.split(path)[0])[0],"AHF_output")
            tmp_path = ahf_path + '/HESTIA_*%.3d.z*AHF_mtree' % snap_id
            cat = glob.glob(tmp_path)[0]
        else:
            raise IOError("Cannot infer path of merger tree files")

    def _load_raw_links(self):
        """
        read in the AHF mtree file containing the indices of halos and its progenitors.
        logic is we read backwards in time which is the opposite to what is done when this function is actually called
        """
        filename = os.path.join(self._path)
        results = np.empty((0,), dtype=np.dtype([('id_this', np.int64), ('id_desc', np.int64), ('Mvir', np.float32)]))

        f = open(filename)
        nhalos = np.loadtxt(f, usecols=(1), dtype=np.int64, max_rows=1) #read only first line
        skip = 1 #skip the first line
        i=0
        while i < nhalos:
            _id, ndesc = np.loadtxt(f, usecols=(1, 2), dtype=np.dtype(np.int64,np.int64), skiprows=skip)
            _id_desc = _id.astype(str)[4:].astype(np.int64) # rip off the timestep which is encoded as the first 3 digits
            
            skip += 1 # increment the skip of lines for the line read above

            results['id_desc'] = np.append(results['id_desc'],[_id_desc]*ndesc)
            
            _this = np.loadtxt(f, usecols=(1), dtype=np.int64, skiprows=skip, max_rows=ndesc)
            _this_id = [x.astype(str)[4:].astype(np.int64) for x in _this] # rip off the timestep which is encoded as the first 3 digits
            
            skip += ndesc # increment line skip by already read lines

            results['this_id'] = np.append(results['this_id'],_id_desc)
            results['Mvir'] = np.append(results['Mvir'], self._Mvir[_this_id])
        
        self.links = results


    def _load_Mvir(self, ts):
        Mvir = ts.calculate_all('Mvir')
        self._Mvir = np.array(Mvir)


    def get_links_for_snapshot(self):
        """Get the links from snapshot ts to its immediate successor.

        Returns a dictionary; keys are the finder IDs at the given snapnum, whereas the values are
        a tuple containing the ID at the subsequent snapshot and the merger ratio (or 1.0 for no merger).
        """

        merger_ratios = self._get_merger_ratio_array(self.links['id_desc'])

        return dict(zip(ids_this_snap, zip(ids_next_snap, merger_ratios)))


    def _get_merger_ratio_array(self, ids_next_snap):

        ratio = np.ones(len(ids_next_snap))
        num_occurences_next_snap = np.bincount(ids_next_snap)
        mergers_next_snap = np.where(num_occurences_next_snap > 1)[0]
        logger.info("Identified %d mergers between snapshots", len(mergers_next_snap))
        for merger in mergers_next_snap:
            contributor_offsets = np.where(ids_next_snap == merger)[0]
            contributing_masses = self.links['Mvir'][contributor_offsets]
            ratio[contributor_offsets] = contributing_masses / contributing_masses.sum()
        return ratio





 