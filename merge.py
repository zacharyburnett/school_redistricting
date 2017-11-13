'''
Created on Nov 8, 2017

@author: Zach
'''

import os
import progressbar

# import from /apps/qgis/python/
from qgis.core import QgsApplication, QgsVectorLayer, QgsDistanceArea, QgsVectorFileWriter, QgsField
#import qgis.utils
#from osgeo import ogr
from PyQt4.QtCore import QVariant
from qgis._core import QgsExpression, QgsFeatureRequest
#from PyQt4.QtGui import *
#from qgis.gui import *

# initialize QGIS application providers
qgs = QgsApplication([], True)
qgs.setPrefixPath('A:/OSGeo4W64/apps/qgis', True)
qgs.initQgis()

# import processing toolbox
from processing.core.Processing import Processing
Processing.initialize()
from processing.tools import general

input_filenames = [
    'B:/Workspaces/GIS/common_data/local/howard_country/Schools_Point/Schools_ElementaryPoint.shp',
    'B:/Workspaces/GIS/common_data/local/howard_country/Schools_Point/Schools_MiddlePoint.shp',
    'B:/Workspaces/GIS/common_data/local/howard_country/Schools_Point/Schools_HighPoint.shp'
]

#general.alghelp("qgis:mergevectorlayers")

#general.runalg("qgis:mergevectorlayers", school_layer, 50, voronoi_filename)

input_param = ';'.join(input_filenames)

output_param = "B:/Workspaces/GIS/GEOG653/final_project/data/schools.shp"

general.runalg("qgis:mergevectorlayers", input_param, output_param)

qgs.exitQgis()
