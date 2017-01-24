# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from geonode.settings import MAP_BASELAYERS, GOOGLE_API_KEY

from geonode.settings import MAP_BASELAYERS
GOOGLE = {
    'maps': {
        'hybrid': {
            'enabled': True,
            'name': 'HYBRID',
            'visibility': False,
        },
        'roadmap': {
            'enabled': True,
            'name': 'ROADMAP',
            'visibility': False,
        },
        'satellite': {
            'enabled': True,
            'name': 'SATELLITE',
            'visibility': False,
        },
        'terrain': {
            'enabled': True,
            'name': 'TERRAIN',
            'visibility': False,
        }
    }
}

for k, v in GOOGLE['maps'].items():
    if v['enabled']:
        BASEMAP = {
            'source': {
                'ptype': 'gxp_googlesource',
                'apiKey': GOOGLE_API_KEY
            },
            'name': v['name'],
            'fixed': True,
            'visibility': v['visibility'],
            'group': 'background'
        }
        MAP_BASELAYERS.append(BASEMAP)
