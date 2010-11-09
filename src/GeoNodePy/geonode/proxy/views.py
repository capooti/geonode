from django.http import HttpResponse
from httplib import HTTPConnection
from urlparse import urlsplit
import httplib2
import urllib
import simplejson 
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger("geonode.proxy.views")

@csrf_exempt
def proxy(request):
    if 'url' not in request.GET:
        return HttpResponse(
                "The proxy service requires a URL-encoded URL as a parameter.",
                status=400,
                content_type="text/plain"
                )

    url = urlsplit(request.GET['url'])
    locator = url.path
    if url.query != "":
        locator += '?' + url.query
    if url.fragment != "":
        locator += '#' + url.fragment

    headers = {}
    if settings.SESSION_COOKIE_NAME in request.COOKIES:
        headers["Cookie"] = request.META["HTTP_COOKIE"]

    conn = HTTPConnection(url.hostname, url.port)
    conn.request(request.method, locator, request.raw_post_data, headers)
    result = conn.getresponse()
    response = HttpResponse(
            result.read(),
            status=result.status,
            content_type=result.getheader("Content-Type", "text/plain")
            )
    return response


@csrf_exempt
def geoserver(request):
    logger.info("GEOSERVER PROXY REQUEST")
    logging.debug("GEOSEREVR PROPROPRPPROXY")
    if not (request.method in ("GET") or request.user.is_authenticated() ):
        return HttpResponse(
            "You must be logged in to access GeoServer",
            mimetype="text/plain",
            status=401
        )
    path = request.get_full_path()[11:] # strip "/geoserver/" from path
    logger.info("PATH IS [%s]", path)
    
    url = "{geoserver}{path}".format(geoserver=settings.GEOSERVER_BASE_URL,path=path)
    logger.info("URL IS [%s]", url)
    h = httplib2.Http()    
    h.add_credentials(*settings.GEOSERVER_CREDENTIALS)
    headers = dict()

    if request.method in ("POST", "PUT") and "CONTENT_TYPE" in request.META:
        headers["Content-Type"] = request.META["CONTENT_TYPE"]
    resp, content = h.request(
            url,
            request.method,
            body=request.raw_post_data or None,
            headers=headers
        )
    if resp.status != 404:
        if "content-type" in resp.keys():
            return HttpResponse(content=content,status=resp.status,mimetype=resp["content-type"])
        else: 
            return HttpResponse(content=content,status=resp.status)
    else: 
        return HttpResponse(content="Something went wrong",status=404)


def picasa(request):
    url = "http://picasaweb.google.com/data/feed/base/all?thumbsize=160c&"
    if request.method == 'GET':
        kind = request.GET['KIND'] if request.method == 'GET' else request.POST['KIND']
        bbox = request.GET['BBOX'] if request.method == 'GET' else request.POST['BBOX']
        query = request.GET['Q'] if request.method == 'GET' else request.POST['Q'] 
        maxResults = request.GET['MAX-RESULTS'] if request.method == 'GET' else request.POST['MAX-RESULTS']
    coords = bbox.split(",")
    coords[0] = coords[0] if coords[0] > -180 else -180
    coords[2] = coords[2] if coords[2]  < 180 else 180
    bbox = str(coords[0]) + ',' + str(coords[1]) + ',' + str(coords[2]) + ',' + str(coords[3])
    url = url + "kind=" + kind + "&max-results=" + maxResults + "&bbox=" + bbox + "&q=" + query
    
    feed_response = urllib.urlopen(url).read()
    return HttpResponse(feed_response, mimetype="text/xml")