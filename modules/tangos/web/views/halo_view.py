from pyramid.view import view_config
import tangos
from tangos import core
import numpy as np

class TimestepInfo(object):
    def __init__(self, ts):
        self.z = "%.2f"%ts.redshift
        self.t = "%.2e Gyr"%ts.time_gyr

class TimeLinks(object):
    def __init__(self, request, halo):
        link_names = ['earliest', '-10', '-1', '+1', '+10', 'latest']
        route_names = ['halo_earlier']*3 + ['halo_later']*3
        ns = ['inf',10,1,1,10,'inf']

        urls = [
            request.route_url(r, simid=halo.timestep.simulation.basename,
                              timestepid=halo.timestep.extension,
                              halonumber=halo.halo_number,
                              n=n)
            for r,n in zip(route_names, ns)
            ]

        self.urls = urls
        self.names = link_names

class DisplayProperty(object):
    def __init__(self, property):
        self.name = property.name.text
        self.value = format_property_data(property)
        self.is_array = property.data_is_array()

class TimeProperty(DisplayProperty):
    def __init__(self, halo):
        self.name = "t()"
        self.value = _number_format(halo.timestep.time_gyr)+" Gyr"
        self.is_array = False

class RedshiftProperty(DisplayProperty):
    def __init__(self, halo):
        self.name = "z()"
        self.value = _number_format(halo.timestep.redshift)
        self.is_array = False

def default_properties(halo):
    properties = [TimeProperty(halo), RedshiftProperty(halo)]

    for property in halo.properties:
        properties.append(DisplayProperty(property))

    return properties

def format_property_data(property):
    data = property.data_raw
    if property.data_is_array():
        if len(data)>5 or len(data.shape)>1:
            return "size "+(" x ".join([str(s) for s in data.shape]))+" array"
        else:
            return "["+(",".join([_number_format(d) for d in data]))+"]"
    else:
        return _number_format(data)

def _number_format(data):
    if np.issubdtype(type(data), np.integer):
        return "%d" % data
    elif np.issubdtype(type(data), np.float):
        if abs(data) > 1e5 or abs(data) < 1e-2:
            return "%.2e" % data
        else:
            return "%.2f" % data


@view_config(route_name='halo_view', renderer='../templates/halo_view.jinja2')
def halo_view(request):
    sim = tangos.get_simulation(request.matchdict['simid'], request.dbsession)
    ts = tangos.get_timestep(request.matchdict['timestepid'], request.dbsession, sim)
    halo = ts.halos.filter_by(halo_number=request.matchdict['halonumber']).first()

    return {'ts_info': TimestepInfo(ts),
            'this_id': halo.id,
            'halonumber': halo.halo_number,
            'timestep': ts.extension,
            'time_links': TimeLinks(request, halo),
            'properties': default_properties(halo)}