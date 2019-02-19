"""Specialised input handler for the  hestia project
http://www.caterpillarproject.org"""

from __future__ import absolute_import

import re
from .. import config
from .pynbody import GadgetSubfindInputHandler
from . import halo_stat_files
import os.path
import pynbody

class HestiaSubfindInputHandler(GadgetSubfindInputHandler):
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
    def _extension_to_filename(self, ts_extension):
        return str(os.path.join(config.base, self.basename, self._pynbody_path_from_snapdir_path(ts_extension)))

    def _is_able_to_load(self, ts_extension):
        try:
            f = pynbody.load(self._pynbody_path_from_snapdir_path(ts_extension))
            h = pynbody.halo.SubfindCatalogue(f)
            return True
        except (IOError, RuntimeError):
            return False

    def load_object(self, ts_extension, halo_number, object_typetag='halo', mode=None):
        if mode=='subfind_properties':
            h = self._construct_halo_cat(self._pynbody_path_from_snapdir_path(ts_extension), object_typetag)
            return h.get_halo_properties(halo_number,with_unit=False)
        else:
            return super(GadgetSubfindInputHandler, self).load_object(self._pynbody_path_from_snapdir_path(ts_extension), halo_number, object_typetag, mode)

    def _construct_group_cat(self, ts_extension):
        f = self.load_timestep(self._pynbody_path_from_snapdir_path(ts_extension))
        h = _loaded_halocats.get(id(f)+1, lambda: None)()
        if h is None:
            h = f.halos()
            assert isinstance(h, pynbody.halo.SubfindCatalogue)
            _loaded_halocats[id(f)+1] = weakref.ref(h)
            f._db_current_groupcat = h  # keep alive for lifetime of simulation
        return h

    def _construct_halo_cat(self, ts_extension, object_typetag):
        if object_typetag== 'halo':
            return super(GadgetSubfindInputHandler, self)._construct_halo_cat(self._pynbody_path_from_snapdir_path(ts_extension), object_typetag)
        elif object_typetag== 'group':
            return self._construct_group_cat(self._pynbody_path_from_snapdir_path(ts_extension))
        else:
            raise ValueError("Unknown halo type %r" % object_typetag)

    def _get_group_children(self,ts_extension):
        h = self._construct_halo_cat(self._pynbody_path_from_snapdir_path(ts_extension), 'halo')
        group_children = {}
        for i in range(len(h)):
            halo_props = h.get_halo_properties(self._pynbody_path_from_snapdir_path(ts_extension),with_unit=False)
            if 'sub_parent' in halo_props:
                parent = halo_props['sub_parent']
                if parent not in group_children:
                    group_children[parent] = []
                group_children[parent].append(i)
        return group_children


    def iterate_object_properties_for_timestep(self, ts_extension, object_typetag, property_names):
        h = self._construct_halo_cat(self._pynbody_path_from_snapdir_path(ts_extension), object_typetag)

        if object_typetag=='halo':
            pynbody_prefix = 'sub_'
        elif object_typetag=='group':
            pynbody_prefix = ""
        else:
            raise ValueError("Unknown object typetag %r"%object_typetag)

        if 'child' in property_names and object_typetag=='group':
            child_map = self._get_group_children(self._pynbody_path_from_snapdir_path(ts_extension))

        for i in range(len(h)):
            all_data = [i]
            for k in property_names:
                pynbody_properties = h.get_halo_properties(i,with_unit=False)
                if pynbody_prefix+k in pynbody_properties:
                    data = self._resolve_units(pynbody_properties[pynbody_prefix+k])
                    if k == 'parent' and data is not None:
                        # turn into a link
                        data = proxy_object.IncompleteProxyObjectFromFinderId(data, 'group')
                elif k=='child' and object_typetag=='group':
                    # subfind does not actually store a list of children; we infer it from the parent
                    # data in the halo catalogue
                    data = child_map.get(i,None)
                    if data is not None:
                        data = [proxy_object.IncompleteProxyObjectFromFinderId(data_i, 'halo') for data_i in data]
                else:
                    data = None

                all_data.append(data)
            yield all_data
