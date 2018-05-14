from BeautifulSoup import BeautifulSoup
import math
import pycurl
from StringIO import StringIO
from centraldb.decorators import cached_call

CIRC_EARTH = 40075000
RADIUS_EARTH = 6367000

def meterDist( u, v):
	lat1, lon1, lat2, lon2 = map(math.radians, [u[0], u[1], v[0], v[1]])

	dlon = lon2 - lon1
	dlat = lat2 - lat1

	a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
	dist = RADIUS_EARTH * 2 * math.asin(math.sqrt(a))

	return dist

def point_projection_on_line(p, seg, testSegmentEnds=False):
	"""
	Planar Projection of a point on a line
        testSegmentEnds limits the projection to the segment, if False, the whole line is used
	"""

	x3,y3 = p
	(x1,y1),(x2,y2) = seg

	dx21 = (x2-x1)
	dy21 = (y2-y1)

	lensq21 = dx21*dx21 + dy21*dy21
        #Check for degenerate segment
	if lensq21 == 0:
	    return (x1, y1)

	u = (x3-x1)*dx21 + (y3-y1)*dy21
	u = u / float(lensq21)

	x = x1+ u * dx21
	y = y1+ u * dy21

	if testSegmentEnds:
	    if u < 0:
	        x,y = x1,y1
	    elif u >1:
	        x,y = x2,y2

	return (x,y)

def point_distance_to_line(p, seg, testSegmentEnds=False):
	"""
	Distance in meters of a point to a line
        testSegmentEnds limits the projection to the segment, if False, the whole line is used
	"""
        projection = point_projection_on_line(p, seg, testSegmentEnds)
        return meterDist(p, projection)



#Openstreetmap tile number to lat/lon converters
def osm_latlon_to_tile_number(lat_deg, lon_deg, zoom):
	""" returns the tile numbers depending on the latitude, longitude and zoom level of a point"""
	lat_rad = math.radians(lat_deg)
	n = 2.0 ** zoom
	xtile = int((lon_deg + 180.0) / 360.0 * n)
	ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
	return (xtile, ytile)

def osm_tile_number_to_latlon(xtile, ytile, zoom):
	""" Returns the latitude and longitude of the north west corner of a tile, based on the tile numbers and the zoom level"""
	n = 2.0 ** zoom
	lon_deg = xtile / n * 360.0 - 180.0
	lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
	lat_deg = math.degrees(lat_rad)
	return (lat_deg, lon_deg)

def osm_tile_number_to_center_latlon(xtile, ytile, zoom):
  """ Returns the latitude and longitude of the center of a tile, based on the tile numbers and the zoom level"""
  lat1, lon1 = osm_tile_number_to_latlon(xtile, ytile, zoom)
  lat2, lon2 = osm_tile_number_to_latlon(xtile +1 , ytile + 1, zoom)
  return ((lat1 + lat2)/2.0, (lon1 +lon2) / 2.0)

def osm_get_raw_data_by_bounding_box(lat_min, lon_min, lat_max, lon_max):
    return osm_query('http://api.openstreetmap.org/api/0.6/map?bbox=%f,%f,%f,%f' % (lon_min,lat_min,lon_max,lat_max))


def osm_get_raw_data_by_tile_numbers(zoom, x, y):
    NW_corner = osm_tile_number_to_latlon(x, y, zoom)
    lat_max, lon_min = NW_corner
    SE_corner = osm_tile_number_to_latlon(x + 1, y + 1, zoom)
    lat_min, lon_max = SE_corner
    return osm_get_raw_data_by_bounding_box(lat_min, lon_min, lat_max, lon_max)

#TODO Implement caching with max age...
@cached_call
def osm_query(url):
    buffer = StringIO()
    c = pycurl.Curl()
    c.setopt(c.URL, url)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()

    body = buffer.getvalue()

    return body



# Extract the GPS coordinates of the roads
# roadSel parameter to pass a list of target road names
# printNames optionnal parameter to print all the detected roads
def extract_roads_from_osm_xml(xml):
	soup = BeautifulSoup(xml)
	Roads = []

	Coordinates = {}

	for point in soup.osm.findAll('node'):
		Coordinates[point['id']] = (float(point['lat']), float(point['lon']))

	for way in soup.osm.findAll(lambda nd : nd.name=="way" and nd.findAll(k='highway')):
		name = ""
		road = []

		nodes = way.findAll('nd')

		#Get the road Name
		for u in nodes[-1].findAll('tag'):
			if u['k'] == 'name':
				name =  u['v']

		for node in nodes:
			road.append(Coordinates[node['ref']])
		Roads.append(road)
	return Roads


def osm_get_streets_from_tiles(target_tiles, osm_zoom):
    retval = []

    for x, y in target_tiles:
        osm_xml = osm_get_raw_data_by_tile_numbers(osm_zoom, x, y)
        for street in extract_roads_from_osm_xml(osm_xml):
            if street not in retval:
                retval.append(street)

    return retval

def osm_get_streets(lat_min, lon_min, lat_max, lon_max):
    osm_xml = osm_get_raw_data_by_bounding_box(lat_min, lon_min, lat_max, lon_max)
    return extract_roads_from_osm_xml(osm_xml)

def pointStyle(name, color, size, stroke_color = '#00000000', stroke_size = 0):
    retval = "'%s': new ol.style.Style({\n\
          image: new ol.style.Circle({\n\
            radius: %d,\n\
            fill: new ol.style.Fill({color: '%s'}),\n\
            stroke: new ol.style.Stroke({ \n\
	            color: '%s', \n\
        	    width: %d \n\
          	}) \n\
          })\n\
        })" % (name, size, color, stroke_color, stroke_size)

    return retval