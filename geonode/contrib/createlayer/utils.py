# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2017 OSGeo
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

import requests
import uuid
import logging
import json

from geoserver.catalog import Catalog

from geonode import GeoNodeException
from geonode.layers.models import Layer
from geonode.geoserver.helpers import ogc_server_settings


logger = logging.getLogger(__name__)

def create_layer(name, title, owner, geometry_type, attributes=None):
    """
    Create an empty layer in GeoServer and register it in GeoNode.
    """
    if not ogc_server_settings.DATASTORE:
        msg = ("To use the createlayer application you must set ogc_server_settings.datastore_db['ENGINE']"
                " to 'django.contrib.gis.db.backends.postgis")
        logger.error(msg)
        raise GeoNodeException(msg)
    else:
        store_name = ogc_server_settings.DATASTORE
    try:
        print 'Creating the layer in GeoServer'
        workspace, datastore = create_gs_layer(store_name, name, title, geometry_type, attributes)
        print 'Creating the layer in GeoNode'
        create_gn_layer(workspace, datastore, name, title, owner)
    except Exception as e:
        print '%s (%s)' % (e.message, type(e))


def create_gn_layer(workspace, datastore, name, title, owner):
    """
    Associate a layer in GeoNode for a given layer in GeoServer.
    """
    layer, created = Layer.objects.create(
        name=name,
        workspace=workspace.name,
        store=datastore.name,
        storeType='dataStore',
        alternate='%s:%s' % (workspace.name, name),
        title=title,
        owner=owner,
        uuid=str(uuid.uuid4()),
        bbox_x0=-180,
        bbox_x1=180,
        bbox_y0=-90,
        bbox_y1=90
    )


def get_attributes(geometry_type, json_fields=None):
    """
    Convert a json representation of fields to a Python representation.

    parameters:

    json_fields
    {
      "field_str": "string",
      "field_int": "integer",
      "field_date": "date",
      "field_float": "float"
    }

    geometry_type: a string which can be "Point", "LineString" or "Polygon"

    Output:
    [
         ['the_geom', u'com.vividsolutions.jts.geom.Polygon', {'nillable': False}],
         ['field_str', 'java.lang.String', {'nillable': True}],
         ['field_int', 'java.lang.Integer', {'nillable': True}],
         ['field_date', 'java.util.Date', {'nillable': True}],
         ['field_float', 'java.lang.Float', {'nillable': True}]
    ]
    """

    lfields = []
    gfield = []
    gfield.append('the_geom')
    gfield.append('com.vividsolutions.jts.geom.%s' % geometry_type)
    gfield.append({'nillable': False})
    lfields.append(gfield)
    if json_fields:
        jfields = json.loads(json_fields)
        for jfield in jfields.items():
            lfield = []
            field_name = jfield[0]
            field_type = jfield[1].lower()
            if field_type not in ('float', 'date', 'string', 'integer'):
                msg = '%s is not a valid type for field %s' % (field_type, field_name)
                logger.error(msg)
                raise GeoNodeException(msg)
            if field_type == 'date':
                field_type = 'java.util.%s' % field_type[:1].upper() + field_type[1:]
            else:
                field_type = 'java.lang.%s' % field_type[:1].upper() + field_type[1:]
            lfield.append(field_name)
            lfield.append(field_type)
            lfield.append({'nillable': True})
            lfields.append(lfield)
    return lfields


def create_gs_layer(store_name, name, title, geometry_type, attributes=None):
    """
    Create an empty PostGIS layer in GeoServer with a given name, title,
    geometry_type and attributes.
    """

    native_name = name
    gs_user = ogc_server_settings.credentials[0]
    gs_password = ogc_server_settings.credentials[1]
    cat = Catalog(ogc_server_settings.internal_rest, gs_user, gs_password)

    # get workspace and store
    workspace = cat.get_default_workspace()
    datastore = cat.get_store(store_name, workspace)

    # check if datastore is of PostGIS type
    if datastore.type != 'PostGIS':
        msg = ("To use the createlayer application you must use PostGIS")
        logger.error(msg)
        raise GeoNodeException(msg)

    # check if layer is existing
    resources = datastore.get_resources()
    for resource in resources:
        if resource.name == name:
            msg = "There is already a layer named %s in %s" % (name, workspace)
            logger.error(msg)
            raise GeoNodeException(msg)

    attributes = get_attributes(geometry_type, attributes)
    attributes_block = "<attributes>"
    empty_opts = {}
    for spec in attributes:
        att_name, binding, opts = spec
        nillable = opts.get("nillable", False)
        attributes_block += ("<attribute>"
                                "<name>{name}</name>"
                                "<binding>{binding}</binding>"
                                "<nillable>{nillable}</nillable>"
                                "</attribute>").format(name=att_name, binding=binding, nillable=nillable)
    attributes_block += "</attributes>"

    # TODO implement others srs and not only EPSG:4326
    xml = ("<featureType>"
            "<name>{name}</name>"
            "<nativeName>{native_name}</nativeName>"
            "<title>{title}</title>"
            "<srs>EPSG:4326</srs>"
            "<latLonBoundingBox><minx>-180</minx><maxx>180</maxx><miny>-90</miny><maxy>90</maxy><crs>EPSG:4326</crs></latLonBoundingBox>"
            "{attributes}"
            "</featureType>").format(
                name=name.encode('UTF-8','strict'), native_name=native_name.encode('UTF-8','strict'),
                title=title.encode('UTF-8','strict'),
                attributes=attributes_block)

    url = '%s/workspaces/%s/datastores/%s/featuretypes' % (ogc_server_settings.internal_rest, workspace.name, datastore.name)
    headers = {'Content-Type': 'application/xml'}
    req = requests.post(url, data=xml, headers=headers, auth=(gs_user, gs_password))
    if req.status_code != 201:
        logger.error('Request status code was: %s' % req.status_code)
        logger.error('Response was: %s' % req.text)
        raise GeoNodeException("Layer could not be created in GeoServer")

    return workspace, datastore
