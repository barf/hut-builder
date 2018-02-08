#!/usr/bin/env python
#
# Convert/ETL DoC huts from ESRI Shapefile to X-Plane DSF
# Stuart MacIntosh <stuart@macintosh.nz>
#
# DSF files/tiles are named by the latitude and longitude of their southwest corner.
# DSF files live in a folder that defines a 10x10 block of tiles, defined by its southwest corner.
# That folder in turn lives in a per-planet folder, which lives in your custom scenery package.
#
# Scenery anatomy:
#
# Earth nav data/
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

#
# Configuration
#

# Abosulte path to DSFTool
dsf_tool = '/home/barf/hut-builder/tools/DSFTool'

# Map of record types in ShapeFile to X-Plane objects
objtype_map = { 
 'Serviced Hut' : 'opensceneryx/objects/buildings/residential/houses/wooden/3.obj',
 'Standard Hut' : 'opensceneryx/objects/buildings/residential/huts/wooden/7.obj',
 'Basic Hut/bivvy' : 'opensceneryx/objects/buildings/residential/huts/wooden/1.obj',
 'Serviced-Alpine Hut' : 'opensceneryx/objects/buildings/residential/houses/wooden/5.obj',
 'Great Walk Hut' : 'opensceneryx/objects/buildings/residential/houses/brick/1.obj'
}

#
# Application
#
# import argparse
import IPython
import shapefile
import os
import subprocess

def make_dsf(bbox, objects_in):
    '''output text file and assemble DSF'''

    rotation = 0

    # add objects in this bbox
    # for objtype, longitude, latitude, rotation in objects:
    objects = list()
    objtypes = list()
    for obj in objects_in:
        objects.append(huts[obj])
        objtypes.append(huts[obj]['objtype'])

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
        out += 'OBJECT_DEF {}\n'.format(objtype_map[objtype])
        objnum_map[objtype] = z
        z += 1

    for obj in objects:
        longitude = obj['pos'][0]
        latitude = obj['pos'][1]
        objnum = objnum_map[obj['objtype']]
        out += 'OBJECT {} {} {} {}\n'.format(objnum, longitude, latitude, rotation)

    return out

def read_shp(shapedatapath):
    '''Parse shapefile and populate a dict.'''

    _huts = dict()

    _sf = shapefile.Reader(shapedatapath)

    print shapedatapath + ': ' + str(_sf.numRecords) + ' records'

    for sr in _sf.shapeRecords():
        status = sr.record[0]
        name = sr.record[1]
        objtype = sr.record[3]
        pos = sr.shape.points

        print 'Reading location: ' + name
        try:
            _huts[name] = { 'pos' : pos[0], 'status' : status, 'objtype' : objtype }
        except:
            print 'error parsing ShapeFile records'
            raise

    return _huts

if __name__=='__main__':
    # argparse goes here

    # parse shapefile
    huts = read_shp("doc-huts/doc-huts")

    # make Earth nav data directory
    try:
        print 'Creating directory: Earth nav data'
        os.mkdir('Earth nav data')
    except:
        print 'exception: directory already exists???'

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
        print 'unable to chdir to "Earth nav data"'
        raise

    for bbox in bboxes_10:
        longitude = bbox[0]
        latitude = bbox[1]

        if longitude > 0:
            longitude = str.format('+{}', longitude)

        if latitude > 0:
            latitude = str.format('+{}', latitude)

        dirname = '{}{}'.format(latitude, longitude)

        print 'Creating directory: {}/'.format(dirname)
        try:
            os.mkdir(dirname)
        except:
            print 'exception: directory already exists???'

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
        print '{}.txt'.format(filename)

        # make dsf text file
        dsf = make_dsf(bbox, hut_map[bbox])
        print dsf

        # makey the text files
        f = open('{}.txt'.format(filename), 'w')
        f.write(dsf)
        f.close()

        subprocess.check_call([dsf_tool,  '--text2dsf', '{}.txt'.format(filename), filename], stderr=subprocess.STDOUT)

    # in case hand assembly required
    # IPython.embed()
