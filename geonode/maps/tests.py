# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2012 OpenPlans
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

from lxml import etree

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from agon_ratings.models import OverallRating

import geonode.maps.models
from geonode.layers.models import Layer
from geonode.maps.models import Map
from geonode.utils import default_map_config
from geonode.search.populate_search_test_data import create_models
from geonode.maps.populate_maplayers import create_maplayers


class MapsTest(TestCase):
    """Tests geonode.maps app/module
    """

    fixtures = ['initial_data.json', 'bobby']

    def setUp(self):
        self.user = 'admin'
        self.passwd = 'admin'
        create_models(type='map')
        create_models(type='layer')
        create_maplayers()

    default_abstract = "This is a demonstration of GeoNode, an application \
for assembling and publishing web based maps.  After adding layers to the map, \
use the Save Map button above to contribute your map to the GeoNode \
community."

    default_title = "GeoNode Default Map"

    # This is a valid map viewer config, based on the sample data provided
    # by andreas in issue 566. -dwins
    viewer_config = """
    {
      "defaultSourceType": "gx_wmssource",
      "about": {
          "title": "Title",
          "abstract": "Abstract"
      },
      "sources": {
        "capra": {
          "url":"http://localhost:8080/geoserver/wms"
        }
      },
      "map": {
        "projection":"EPSG:900913",
        "units":"m",
        "maxResolution":156543.0339,
        "maxExtent":[-20037508.34,-20037508.34,20037508.34,20037508.34],
        "center":[-9428760.8688778,1436891.8972581],
        "layers":[{
          "source":"capra",
          "buffer":0,
          "wms":"capra",
          "name":"base:nic_admin"
        }],
        "keywords":["saving", "keywords"],
        "zoom":7
      }
    }
    """

    viewer_config_alternative = """
    {
      "defaultSourceType": "gx_wmssource",
      "about": {
          "title": "Title2",
          "abstract": "Abstract2"
      },
      "sources": {
        "capra": {
          "url":"http://localhost:8080/geoserver/wms"
        }
      },
      "map": {
        "projection":"EPSG:900913",
        "units":"m",
        "maxResolution":156543.0339,
        "maxExtent":[-20037508.34,-20037508.34,20037508.34,20037508.34],
        "center":[-9428760.8688778,1436891.8972581],
        "layers":[{
          "source":"capra",
          "buffer":0,
          "wms":"capra",
          "name":"base:nic_admin"
        }],
        "zoom":7
      }
    }
    """

    perm_spec = {"anonymous":"_none","authenticated":"_none","users":[["admin","map_readwrite"]]}

    def test_map_json(self):
        c = Client()
        # Test that saving a map when not logged in gives 401
        response = c.put(reverse('map_json', args=('1',)),data=self.viewer_config,content_type="text/json")
        self.assertEqual(response.status_code, 401)

        c.login(username=self.user, password=self.passwd)
        response = c.put(reverse('map_json', args=('1',)),data=self.viewer_config_alternative,content_type="text/json")
        self.assertEqual(response.status_code, 200)

        map_obj = Map.objects.get(id=1)
        self.assertEquals(map_obj.title, "Title2")
        self.assertEquals(map_obj.abstract, "Abstract2")
        self.assertEquals(map_obj.layer_set.all().count(), 1)

    def test_map_save(self):
        """POST /maps/new/data -> Test saving a new map"""

        c = Client()
        new_map = reverse("new_map_json")
        # Test that saving a map when not logged in gives 401
        response = c.post(new_map,data=self.viewer_config,content_type="text/json")
        self.assertEqual(response.status_code,401)

        # Test successful new map creation
        c.login(username=self.user, password=self.passwd)
        response = c.post(new_map,data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])
        c.logout()

        # We have now 9 maps and 8 layers so the next pk will be 18
        self.assertEquals(map_id,18)
        map_obj = Map.objects.get(id=map_id)
        self.assertEquals(map_obj.title, "Title")
        self.assertEquals(map_obj.abstract, "Abstract")
        self.assertEquals(map_obj.layer_set.all().count(), 1)
        self.assertEquals(map_obj.keyword_list(), [u"keywords", u"saving"])

        # Test an invalid map creation request
        c.login(username=self.user, password=self.passwd)
        response = c.post(new_map,data="not a valid viewer config",content_type="text/json")
        self.assertEquals(response.status_code,400)
        c.logout()

    def test_map_fetch(self):
        """/maps/[id]/data -> Test fetching a map in JSON"""
        map_obj = Map.objects.get(id=1)
        map_obj.set_default_permissions()
        c = Client()
        response = c.get(reverse('map_json', args=(map_obj.id,)))
        self.assertEquals(response.status_code, 200)
        cfg = json.loads(response.content)
        self.assertEquals(cfg["about"]["abstract"], 'GeoNode default map abstract')
        self.assertEquals(cfg["about"]["title"], 'GeoNode Default Map')
        self.assertEquals(len(cfg["map"]["layers"]), 5)

    def test_map_to_json(self):
        """ Make some assertions about the data structure produced for serialization
            to a JSON map configuration"""
        map_obj = Map.objects.get(id=1)
        cfg = map_obj.viewer_json()
        self.assertEquals(cfg['about']['abstract'], 'GeoNode default map abstract')
        self.assertEquals(cfg['about']['title'], 'GeoNode Default Map')
        def is_wms_layer(x):
            return cfg['sources'][x['source']]['ptype'] == 'gxp_wmscsource'
        layernames = [x['name'] for x in cfg['map']['layers'] if is_wms_layer(x)]
        self.assertEquals(layernames, ['base:CA',])

    def test_map_to_wmc(self):
        """ /maps/1/wmc -> Test map WMC export
            Make some assertions about the data structure produced
            for serialization to a Web Map Context Document
        """

        map_obj = Map.objects.get(id=1)
        map_obj.set_default_permissions()
        c = Client()
        response = c.get(reverse('map_wmc', args=(map_obj.id,)))
        self.assertEquals(response.status_code, 200)

        # check specific XPaths
        wmc = etree.fromstring(response.content)

        namespace = '{http://www.opengis.net/context}'
        title = '{ns}General/{ns}Title'.format(ns=namespace)
        abstract = '{ns}General/{ns}Abstract'.format(ns=namespace)

        self.assertEquals(wmc.attrib.get('id'), '1')
        self.assertEquals(wmc.find(title).text, 'GeoNode Default Map')
        self.assertEquals(wmc.find(abstract).text, 'GeoNode default map abstract')

    def test_newmap_to_json(self):
        """ Make some assertions about the data structure produced for serialization
            to a new JSON map configuration"""
        response = Client().get(reverse('new_map_json'))
        cfg = json.loads(response.content)
        self.assertEquals(cfg['defaultSourceType'], "gxp_wmscsource")

    def test_map_details(self):
        """/maps/1 -> Test accessing the map browse view function"""
        map_obj = Map.objects.get(id=1)
        map_obj.set_default_permissions()
        c = Client()
        response = c.get(reverse('map_detail', args=(map_obj.id,)))
        self.assertEquals(response.status_code,200)

    def test_new_map_without_layers(self):
        # TODO: Should this test have asserts in it?
        client = Client()
        client.get(reverse('new_map'))

    def test_new_map_with_layer(self):
        client = Client()
        layer = Layer.objects.all()[0]
        client.get(reverse('new_map') +'?layer=' + layer.typename)

    def test_new_map_with_empty_bbox_layer(self):
        client = Client()
        layer = Layer.objects.all()[0]
        client.get(reverse('new_map') +'?layer=' + layer.typename)

    def test_ajax_map_permissions(self):
        """Verify that the ajax_layer_permissions view is behaving as expected
        """

        # Setup some layer names to work with
        mapid = Map.objects.all()[0].pk
        invalid_mapid = "42"

        c = Client()

        url = lambda id: reverse('map_permissions',args=[id])

        # Test that an invalid layer.typename is handled for properly
        response = c.post(url(invalid_mapid),
                          data=json.dumps(self.perm_spec),
                          content_type="application/json")
        self.assertEquals(response.status_code, 404)

        # Test that GET returns permissions
        response = c.get(url(mapid))
        assert('permissions' in response.content)

        # Test that a user is required to have permissions

        # First test un-authenticated
        response = c.post(url(mapid),
                          data=json.dumps(self.perm_spec),
                          content_type="application/json")
        self.assertEquals(response.status_code, 401)

        # Next Test with a user that does NOT have the proper perms
        logged_in = c.login(username='bobby', password='bob')
        self.assertEquals(logged_in, True)
        response = c.post(url(mapid),
                          data=json.dumps(self.perm_spec),
                          content_type="application/json")
        self.assertEquals(response.status_code, 401)

        # Login as a user with the proper permission and test the endpoint
        logged_in = c.login(username='admin', password='admin')
        self.assertEquals(logged_in, True)

        response = c.post(url(mapid),
                          data=json.dumps(self.perm_spec),
                          content_type="application/json")

        # Test that the method returns 200
        self.assertEquals(response.status_code, 200)

        # Test that the permissions specification is applied


    def test_map_metadata(self):
        """Test that map metadata can be properly rendered
        """
        # first create a map
        c = Client()

        # Test successful new map creation
        c.login(username=self.user, password=self.passwd)
        new_map = reverse('new_map_json')
        response = c.post(new_map, data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])
        c.logout()

        url = reverse('map_metadata', args=(map_id,))

        # test unauthenticated user to modify map metadata
        response = c.post(url)
        self.assertEquals(response.status_code,302)

        # test a user without metadata modify permission
        c.login(username='norman', password='norman')
        response = c.post(url)
        self.assertEquals(response.status_code, 302)
        c.logout()

        # Now test with a valid user using GET method
        c.login(username=self.user, password=self.passwd)
        response = c.get(url)
        self.assertEquals(response.status_code, 200)

        # Now test with a valid user using POST method
        c.login(username=self.user, password=self.passwd)
        response = c.post(url)
        self.assertEquals(response.status_code, 200)

        # TODO: only invalid mapform is tested


    def test_map_remove(self):
        """Test that map can be properly removed
        """
        # first create a map
        c = Client()

        # Test successful new map creation
        c.login(username=self.user, password=self.passwd)
        new_map = reverse('new_map_json')
        response = c.post(new_map, data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])
        c.logout()

        url = reverse('map_remove', args=(map_id,))

        # test unauthenticated user to remove map
        response = c.post(url)
        self.assertEquals(response.status_code,302)

        # test a user without map removal permission
        c.login(username='norman', password='norman')
        response = c.post(url)
        self.assertEquals(response.status_code, 302)
        c.logout()

        # Now test with a valid user using GET method
        c.login(username=self.user, password=self.passwd)
        response = c.get(url)
        self.assertEquals(response.status_code, 200)

        # Now test with a valid user using POST method,
        # which removes map and associated layers, and redirects webpage
        response = c.post(url)
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'], 'http://testserver/maps/')

        # After removal, map is not existent
        response = c.get(url)
        self.assertEquals(response.status_code, 404)

        #Prepare map object for later test that if it is completely removed
        #map_obj = Map.objects.get(id=1)

        # TODO: Also associated layers are not existent
        #self.assertEquals(map_obj.layer_set.all().count(), 0)


    def test_map_embed(self):
        """Test that map can be properly embedded
        """
        # first create a map
        c = Client()

        # Test successful new map creation
        c.login(username=self.user, password=self.passwd)

        new_map = reverse('new_map_json')
        response = c.post(new_map, data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])
        c.logout()

        url = reverse('map_embed', args=(map_id,))
        url_no_id = reverse('map_embed')

        # Now test with a map id
        c.login(username=self.user, password=self.passwd)
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        # Config equals to that of the map whose id is given
        map_obj = Map.objects.get(id=map_id)
        config_map = map_obj.viewer_json()
        response_config_dict = json.loads(response.context['config'])
        self.assertEquals(config_map['about']['abstract'],response_config_dict['about']['abstract'])
        self.assertEquals(config_map['about']['title'],response_config_dict['about']['title'])

        # Now test without a map id
        response = c.get(url_no_id)
        self.assertEquals(response.status_code, 200)
        # Config equals to that of the default map
        config_default = default_map_config()[0]
        response_config_dict = json.loads(response.context['config'])
        self.assertEquals(config_default['about']['abstract'],response_config_dict['about']['abstract'])
        self.assertEquals(config_default['about']['title'],response_config_dict['about']['title'])


    def test_map_view(self):
        """Test that map view can be properly rendered
        """
        # first create a map
        c = Client()

        # Test successful new map creation
        c.login(username=self.user, password=self.passwd)

        new_map = reverse('new_map_json')
        response = c.post(new_map, data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])
        c.logout()

        url = reverse('map_view', args=(map_id,))

        # test unauthenticated user to view map
        response = c.get(url)
        self.assertEquals(response.status_code,200)
        # TODO: unauthenticated user can still access the map view

        # test a user without map view permission
        c.login(username='norman', password='norman')
        response = c.get(url)
        self.assertEquals(response.status_code, 200)
        c.logout()
        # TODO: the user can still access the map view without permission

        # Now test with a valid user using GET method
        c.login(username=self.user, password=self.passwd)
        response = c.get(url)
        self.assertEquals(response.status_code, 200)

        # Config equals to that of the map whose id is given
        map_obj = Map.objects.get(id=map_id)
        config_map = map_obj.viewer_json()
        response_config_dict = json.loads(response.context['config'])
        self.assertEquals(config_map['about']['abstract'],response_config_dict['about']['abstract'])
        self.assertEquals(config_map['about']['title'],response_config_dict['about']['title'])


    def test_new_map_config(self):
        """Test that new map config can be properly assigned
        """
        c = Client()
        c.login(username='admin', password='admin')

        # Test successful new map creation
        m = Map()
        admin_user = User.objects.get(username='admin')
        layer_name = Layer.objects.all()[0].typename
        m.create_from_layer_list(admin_user, [layer_name], "title", "abstract")
        map_id = m.id

        c = Client()

        url = reverse('new_map_json')

        # Test GET method with COPY
        response = c.get(url,{'copy': map_id})
        self.assertEquals(response.status_code,200)
        map_obj = Map.objects.get(id=map_id)
        config_map = map_obj.viewer_json()
        response_config_dict = json.loads(response.content)
        self.assertEquals(config_map['map']['layers'],response_config_dict['map']['layers'])

        # Test GET method no COPY and no layer in params
        response = c.get(url)
        self.assertEquals(response.status_code,200)
        config_default = default_map_config()[0]
        response_config_dict = json.loads(response.content)
        self.assertEquals(config_default['about']['abstract'],response_config_dict['about']['abstract'])
        self.assertEquals(config_default['about']['title'],response_config_dict['about']['title'])

        # Test GET method no COPY but with layer in params
        response = c.get(url,{'layer':layer_name})
        self.assertEquals(response.status_code,200)
        response_dict = json.loads(response.content)
        self.assertEquals(response_dict['fromLayer'],True)

        # Test POST method without authentication
        response = c.post(url,{'layer':layer_name})
        self.assertEquals(response.status_code,401)

        # Test POST method with authentication and a layer in params
        c.login(username='admin', password='admin')

        response = c.post(url,{'layer':layer_name})
        # Should not accept the request
        self.assertEquals(response.status_code,400)

        # Test POST method with map data in json format
        response = c.post(url, data=self.viewer_config,content_type="text/json")
        self.assertEquals(response.status_code,200)
        map_id = int(json.loads(response.content)['id'])

        # Test methods other than GET or POST and no layer in params
        response = c.put(url)
        self.assertEquals(response.status_code,405)


    def test_rating_map_remove(self):
        """Test map rating is removed on map remove
        """
        c = Client()
        c.login(username=self.user, password=self.passwd)

        new_map = reverse('new_map_json')

        #Create the map
        response = c.post(new_map, data=self.viewer_config,content_type="text/json")
        map_id = int(json.loads(response.content)['id'])

        #Create the rating with the correct content type
        ctype = ContentType.objects.get(model='map')
        OverallRating.objects.create(category=1,object_id=map_id,content_type=ctype, rating=3)

        #Remove the map
        response = c.post(reverse('map_remove', args=(map_id,)))
        self.assertEquals(response.status_code,302)

        #Check there are no ratings matching the removed map
        rating = OverallRating.objects.filter(category=1,object_id=map_id)
        self.assertEquals(rating.count(),0)

