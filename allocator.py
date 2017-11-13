from qgis.core import *
QgsApplication.setPrefixPath("A:/OSGeo4W64/apps/qgis", True)
qgs = QgsApplication([], False)
qgs.initQgis()

# Write your code here to load some layers, use processing algorithms, etc.

# define schools shapefile filenames
schools = {
    "elementary" = "B:\Workspaces\GIS\common_data\local\howard_country\Schools_Elementary\Schools_ElementaryPoint.shp",
    "middle" = "B:\Workspaces\GIS\common_data\local\howard_country\Schools_Middle\Schools_MiddlePoint.shp",
    "high" = "B:\Workspaces\GIS\common_data\local\howard_country\Schools_High\Schools_HighPoint.shp"
}

for school_type in schools:
    schools[school_type] = iface.addVectorLayer(schools[school_type], "schools_" + schools_type, "ogr")

qgs.exitQgis()
