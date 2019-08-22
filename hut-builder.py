#!/usr/bin/env python3
#
# Map/Convert/ETL points from ESRI Shapefile to X-Plane DSF objects
# Stuart MacIntosh <stuart@macintosh.nz>
#
## About DSF files:
# DSF files/tiles are named by the latitude and longitude of their southwest corner.
# DSF files live in a folder that defines a 10x10 block of tiles, defined by its southwest corner.
# That folder in turn lives in a per-planet folder, which lives in your custom scenery package.
#
## Scenery anatomy:
#
# foo_scenery/Earth nav data/
#     -40+170/
#         -36+173.dsf
#     -50+170/
#         -42+174.dsf
#           # PROPERTY sim/west 174
#           # PROPERTY sim/east 175
#           # PROPERTY sim/north -41
#           # PROPERTY sim/south -42
#     -50-180/
#         -44-177.dsf
#
# Required DSF properties
# sim/west    (Required)  The western edge of the DSF file in degrees longitude.
# sim/east    (Required)  The eastern edge of the DSF file in degrees longitude.
# sim/south   (Required)  The northern edge of the DSF file in degrees latitude.
# sim/north   (Required)  The southern edge of the DSF file in degrees latitude.

# Debug / Configuration
DEBUG = False

# Abosulte path to DSFTool
dsf_tool = '/home/barf/X-Plane 11/tools/DSFTool'

# Spatial Reference System
input_CRS_EPSG = 2193
output_CRS_EPSG = 4326

# Map of record types in ShapeFile to X-Plane objects
objtype_map = { 
 '_default' : 'opensceneryx/objects/buildings/residential/huts/wooden/1.obj',
 'Serviced Hut' : 'opensceneryx/objects/buildings/residential/houses/wooden/3.obj',
 'Standard Hut' : 'opensceneryx/objects/buildings/residential/huts/wooden/7.obj',
 'Basic Hut/bivvy' : 'opensceneryx/objects/buildings/residential/huts/wooden/1.obj',
 'Serviced-Alpine Hut' : 'opensceneryx/objects/buildings/residential/houses/wooden/5.obj',
 'Great Walk Hut' : 'opensceneryx/objects/buildings/residential/houses/brick/1.obj',
 'rock' : 'opensceneryx/objects/buildings/residential/huts/wooden/1.obj',
}

#
# The Application
#
from IPython import embed
from osgeo import ogr
from osgeo import osr
import shapefile
import os
import subprocess
import argparse
import json

# transform function
def transform_xy(x, y):
    point = ogr.CreateGeometryFromWkt("POINT (%s %s)" % (x, y))
    point.Transform(transform)
    return json.loads(point.ExportToJson())['coordinates']

# output function
def make_dsf(bbox, objects_in):
    '''output text file and assemble DSF'''

    rotation = 0

    # add objects in this bbox
    # for objtype, longitude, latitude, rotation in objects:
    objects = list()
    objtypes = list()
    for obj in objects_in:
        try:
            objects.append(huts[obj])
            objtypes.append(huts[obj]['objtype'])
        except e:
            if DEBUG: embed()
            exit(1)

    # make set of object types here
    objtypes = set(objtypes)

    # header
    out = '''A\n800\nDSFTool\n'''

    # properties
    out += 'PROPERTY sim/north {}\n'.format(bbox[1] + 1)
    out += 'PROPERTY sim/south {}\n'.format(bbox[1])
    out += 'PROPERTY sim/east {}\n'.format(bbox[0] + 1)
    out += 'PROPERTY sim/west {}\n'.format(bbox[0])
    out += 'PROPERTY sim/planet earth\n'
    out += 'PROPERTY sim/require_object 1/0\n'
    out += 'PROPERTY sim/overlay 1\n'
    out += 'PROPERTY sim/author Stuart MacIntosh\n'
    out += 'PROPERTY sim/creation_agent hut-builder.py\n'
    
    # add objects definitions for each obj in this DSF
    objnum_map = dict()
    z = 0
    for objtype in objtypes:
        try:
            out += 'OBJECT_DEF {}\n'.format(objtype_map[objtype])
            objnum_map[objtype] = z
            z += 1
        except:
            print('Error mapping object types')
            if DEBUG: embed()
            exit(1)

    for obj in objects:
        try:
            longitude = obj['pos'][0]
            latitude = obj['pos'][1]
            objnum = objnum_map[obj['objtype']]
            out += 'OBJECT {} {} {} {}\n'.format(objnum, longitude, latitude, rotation)
        except:
            print('OBJECT output error')
            embed()
            exit(1)

    return out

# input function
def read_shp(shapedatapath):
    '''Parse shapefile and populate a dict.'''

    _huts = dict()

    _sf = shapefile.Reader(shapedatapath)

    print(shapedatapath + ': ' + str(_sf.numRecords) + ' records')

    # pause before processing
    if DEBUG:
        print(_sf.shapeTypeName)
        print(_sf.fields)
        # print('DEBUGGING - read_shp()')
        # embed()

    for sr in _sf.shapeRecords():
        # [('DeletionFlag', 'C', 1, 0), ['t50_fid', 'N', 9, 0], ['status', 'C', 8, 0], ['materials', 'C', 4, 0], ['name_ascii', 'C', 75, 0], ['macronated', 'C', 1, 0], ['name', 'C', 75, 0]]
        try:
            if DEBUG: print(sr.record)

            status = sr.record['status']
            name = sr.record['name']
            name_ascii = sr.record['name_ascii']
            if len(sr.record['materials']) == 0:
                objtype = '_default'
            else:
                objtype = sr.record['materials']
            
            pos = transform_xy(sr.shape.points[0][0], sr.shape.points[0][1])

            print('Adding: ' + name)
            _huts[name] = { 'pos' : pos, 'status' : status, 'objtype' : objtype }
        except:
            print('Error parsing ShapeFile records')
            embed()
            exit(1)

    return _huts

if __name__=='__main__':
    # argparse goes here
    parser = argparse.ArgumentParser(description='Process some ESRI ShapeFiles into X-Plane DSF scenery objects.')
    parser.add_argument('shapefile', type=str, nargs=1, help='path to input shapefile')
    parser.add_argument('--debug', action='store_true', help='interactive debug mode')
    args = parser.parse_args()
    if args.debug: DEBUG = True

    # setup GDAL reprojection API
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(input_CRS_EPSG) # TODO # get from shapefile

    target_crs = osr.SpatialReference()
    target_crs.ImportFromEPSG(output_CRS_EPSG)

    transform = osr.CoordinateTransformation(source_crs, target_crs)

    # test for DSFTool
    # if not os.path.isfile(dsf_tool) or not os.path.isfile('DSFTool'):
    if not os.path.isfile(dsf_tool):
        print('Error - DSFTool not found')
        parser.print_help()
        exit(1)
    
    # open shapefile and parse data
    try:
        huts = read_shp(os.path.abspath(args.shapefile[0]))
    except:
        print('error opening shapefile')
        if DEBUG: embed()
        exit(1)

    # create scenery directory
    base_name = os.path.basename(args.shapefile[0])
    if '.shp' not in base_name[-4:].lower():
        print('Error - input file does not have .shp extension')
        exit(1)
    base_name = base_name[:-4]
    if os.path.isdir(base_name):
        print('Error - %s directory already exists' % base_name)
        exit(1)
    try:
        os.mkdir(base_name)
        os.chdir(os.curdir + os.sep + base_name)
    except:
        print('Error creating directory')
        if DEBUG: embed()
        exit(1)

    # make 'Earth nav data' directory in cwd if not already there
    if os.path.isdir('Earth nav data'):
        print('Error - "Earth nav data" directory already exists')
        exit(1)
    try:
        print('Creating directory: Earth nav data')
        os.mkdir('Earth nav data')
    except:
        if DEBUG: embed()
        exit(1)

    # divide objects into DSF-sized bounding boxes
    bboxes_10 = list()
    # populat a list of 10 degree sized boxes
    for hut in huts.keys():
        longitude = int(huts[hut]['pos'][0] - huts[hut]['pos'][0] % 10)
        latitude = int(huts[hut]['pos'][1] - huts[hut]['pos'][1] % 10)
        bboxes_10.append((longitude, latitude))

    # yay for python makings sets from tuples
    bboxes_10 = set(bboxes_10)

    try:
        os.chdir('Earth nav data')
    except:
        print('unable to chdir to "Earth nav data"')
        raise

    for bbox in bboxes_10:
        longitude = bbox[0]
        latitude = bbox[1]

        if longitude > 0:
            longitude = str.format('+{}', longitude)

        if latitude > 0:
            latitude = str.format('+{}', latitude)

        dirname = '{}{}'.format(latitude, longitude)

        print('Creating directory: {}/'.format(dirname))
        try:
            os.mkdir(dirname)
        except:
            print('exception: directory already exists???')

    # create 1x1 degree DSF files
    bboxes_1 = list()
    for hut in huts.keys():
        # TODO: fix east/west of meridian issue?
        longitude = int(huts[hut]['pos'][0] - huts[hut]['pos'][0] % 1)
        latitude = int(huts[hut]['pos'][1] - huts[hut]['pos'][1] % 1)
        bboxes_1.append((longitude, latitude))

    bboxes_1 = set(bboxes_1)

    hut_map = dict()
    for hut in huts.keys():
        longitude = int(huts[hut]['pos'][0] - huts[hut]['pos'][0] % 1)
        latitude = int(huts[hut]['pos'][1] - huts[hut]['pos'][1] % 1)
        if (longitude, latitude) not in hut_map.keys():
            hut_map[(longitude, latitude)] = [hut]
        else:
            hut_map[(longitude, latitude)].append(hut)

    for bbox in bboxes_1:
        # we're in a 1x1 bbox
        longitude = bbox[0]
        latitude = bbox[1]

        if longitude > 0:
            longitude = str.format('+{}', longitude)

        if latitude > 0:
            latitude = str.format('+{}', latitude)

        # the 10x10 box please
        longitude_10 = int(bbox[0] - bbox[0] % 10)
        latitude_10 = int(bbox[1] - bbox[1] % 10)

        if longitude_10 > 0:
            longitude_10 = str.format('+{}', longitude_10)

        if latitude_10 > 0:
            latitude_10 = str.format('+{}', latitude_10)  

        #
        filename = '{}{}/{}{}.dsf'.format(latitude_10, longitude_10, latitude, longitude)
        print('{}.txt'.format(filename))

        # make dsf text file
        dsf = make_dsf(bbox, hut_map[bbox])
        print(dsf)

        # makey the text files
        f = open('{}.txt'.format(filename), 'w')
        f.write(dsf)
        f.close()

        subprocess.check_call([dsf_tool,  '--text2dsf', '{}.txt'.format(filename), filename], stderr=subprocess.STDOUT)

    # in case hand assembly required
    # IPython.embed()
