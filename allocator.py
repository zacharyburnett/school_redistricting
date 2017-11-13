'''
Created on Nov 6, 2017

@author: Zach
'''

import os
import pandas
import progressbar

# import from /apps/qgis/python/
from qgis.core import QgsApplication, QgsVectorLayer, QgsFeatureRequest, QgsExpression, QgsVectorFileWriter
from qgis.core import QgsField, QgsPoint, QgsDistanceArea, QgsCoordinateReferenceSystem, NULL
#import qgis.utils
#from osgeo import ogr
from PyQt4.QtCore import QVariant
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

#Create a measure object
distance_area = QgsDistanceArea()
crs = QgsCoordinateReferenceSystem()
crs.createFromSrsId(3452) # EPSG:4326
distance_area.setSourceCrs(crs)
distance_area.setEllipsoidalMode(True)
distance_area.setEllipsoid('WGS84')

# define number of iterations to complete
num_iterations = 1

# define school levels
school_levels = ['elem', 'midd', 'high']

# define output directory
output_dir = "B:/Workspaces/GIS/GEOG653/final_project/output/"

# define filenames
attendance_areas_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\MPIA\FS17_COMpolys.shp"
school_capacities_filenames = {
    'elem': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_elem.csv",
    'midd': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_midd.csv",
    'high': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_high.csv"
    }
schools_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\schools.shp"
enrollment_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\EnrollmentHousing.csv"

# load vector data
general.runalg("qgis:reprojectlayer", schools_filename, "epsg:4326", os.path.join(output_dir, "schools.shp"))
schools_layer = QgsVectorLayer(os.path.join(output_dir, "schools.shp"), 'schools', 'ogr')
general.runalg("qgis:reprojectlayer", attendance_areas_filename, "epsg:4326", os.path.join(output_dir, "attendance_areas.shp"))
attendance_areas_layer = QgsVectorLayer(os.path.join(output_dir, "attendance_areas.shp"), 'attendance_areas', 'ogr')

bar = progressbar.ProgressBar(max_value=len(school_levels) * (num_iterations + 3))
bar_counter = 0
bar.update(bar_counter)

enrollment_dataframe = pandas.read_csv(enrollment_filename)
enrollment_population_fields = {
    'elem': ['GR0_POP', 'GR1_POP', 'GR2_POP', 'GR3_POP', 'GR4_POP', 'GR5_POP'],
    'midd': ['GR6_POP', 'GR7_POP', 'GR8_POP'],
    'high': ['GR9_POP', 'GR10_POP', 'GR11_POP', 'GR12_POP']
    }

attendance_area_populations = {}

for school_level in school_levels:
    attendance_area_populations[school_level] = dict(zip(enrollment_dataframe['PLAN_ID'], sum([enrollment_dataframe[population_field] for population_field in enrollment_population_fields[school_level]])))

# populations = {}
# 
# for plan_id in [attendance_area['PLAN_ID'] for attendance_area in attendance_areas_layer.getFeatures()]:
#     populations[plan_id] = {}
# 
# for school_level, area_populations in attendance_area_populations.iteritems():
#     for plan_id, population in area_populations.iteritems():
#         populations[plan_id][school_level] = population
# 
# for plan_id, school_levels in populations.iteritems():
#     print "%s,%s" % (plan_id, ",".join(str(x) for x in school_levels.values()))

school_capacities = {}

for school_level in school_levels:
    school_capacities_dataframe = pandas.read_csv(school_capacities_filenames[school_level])
    school_capacities[school_level] = dict(zip(school_capacities_dataframe['school'], school_capacities_dataframe['capacity']))
    
target_min_utilization = 90
target_max_utilization = 110

school_populations = {}
current_school_populations = {}

school_utilizations = {}
current_school_utilizations = {}
thiessen_layer = {}

for school_level in school_levels:
    bar_counter = bar_counter + 1
    bar.update(bar_counter)
           
    if school_level == 'elem':
        school_level_key = 'ES_HOME'
    elif school_level == 'midd':
        school_level_key = 'MS_HOME'
    elif school_level == 'high':
        school_level_key = 'HS_HOME'
        
    schools = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" LIKE '%%%s%%'" % (school_level_key[0:2]))))
    school_names = [school['Name'] for school in schools]
           
    # find current school utilizations by capacity
    current_school_populations[school_level] = {}
    current_school_utilizations[school_level] = {}
    for school_name in school_names:
        school_population = sum([attendance_area_populations[school_level][attendance_area['PLAN_ID']] for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level_key, school_name))))])
        current_school_populations[school_level][school_name] = school_population
        current_school_utilizations[school_level][school_name] = school_population * 100 / school_capacities[school_level][school_name]
     
    # calculate Voronoi (Thiessen) polygons
    voronoi_filename = os.path.join(output_dir, 'voronoi_%s_school.shp' % (school_level))
    if not os.path.exists(voronoi_filename):
        voronoi_temp_filename = os.path.join(output_dir, 'voronoi_%s_school_temp.shp' % (school_level))
        general.runalg("qgis:selectbyattribute", schools_layer, "Level", 7, school_level)
        general.runalg("saga:thiessenpolygons", schools_layer, 0.2, voronoi_temp_filename)
        general.runalg("qgis:clip",voronoi_temp_filename, os.path.join(output_dir, "attendance_areas.shp"), voronoi_filename)
    voronoi_layer = QgsVectorLayer(voronoi_filename, 'voronoi_%s_school' % (school_level), 'ogr')

    bar_counter = bar_counter + 1
    bar.update(bar_counter)
    
    # add new field
    if school_level not in [field.name() for field in attendance_areas_layer.fields()]:
        attendance_areas_layer.dataProvider().addAttributes([QgsField(school_level, QVariant.String)])
        attendance_areas_layer.updateFields()
        
    attendance_areas_layer.startEditing()
    
    # find attendance areas within voronoi polygons
    for attendance_area in attendance_areas_layer.getFeatures():
        for voronoi_polygon in voronoi_layer.getFeatures():
            if attendance_area.geometry().within(voronoi_polygon.geometry()):
                attendance_area[school_level] = voronoi_polygon['Name']
                attendance_areas_layer.updateFeature(attendance_area)
                break
    
    home_areas = {}
    
    for school in schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" LIKE '%%%s%%'" % (school_level_key[0:2])))):
        for attendance_area in attendance_areas_layer.getFeatures():
            if school.geometry().within(attendance_area.geometry()):
                home_areas[school['Name']] = attendance_area['PLAN_ID']
                attendance_area[school_level] = school['Name']
                attendance_areas_layer.updateFeature(attendance_area)
    
#     # find attendance areas intersecting voronoi polygons and assign them to their highest area intersection
#     intersecting_voronoi = {}
#     for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" IS NULL" % (school_level)))):
#         intersecting_voronoi[attendance_area['PLAN_ID']] = {}
#         for voronoi_polygon in voronoi_layer.getFeatures():
#             school_name = voronoi_polygon['Name']
#             if attendance_area.geometry().intersects(voronoi_polygon.geometry()):
#                 intersecting_voronoi[attendance_area['PLAN_ID']][school_name] = attendance_area.geometry().intersection(voronoi_polygon.geometry()).area()
#                 #intersecting_voronoi[attendance_area['PLAN_ID']][school_name] = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
#                 if attendance_area[school_level] == NULL or (intersecting_voronoi[attendance_area['PLAN_ID']][school_name] > intersecting_voronoi[attendance_area['PLAN_ID']][attendance_area[school_level]]):
#                     attendance_area[school_level] = school_name
#                     attendance_areas_layer.updateFeature(attendance_area)

    attendance_areas_layer.commitChanges()
    
    bar_counter = bar_counter + 1
    bar.update(bar_counter)
             
    # find school utilizations by capacity
    school_populations[school_level] = {}
    school_utilizations[school_level] = {}
    for school_name in school_names:
        school_population = sum([attendance_area_populations[school_level][attendance_area['PLAN_ID']] for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))])
        school_populations[school_level][school_name] = school_population
        school_utilizations[school_level][school_name] = school_population * 100 / school_capacities[school_level][school_name]
    
    attendance_areas_to_update = {}
    
    null_attendance_areas = [attendance_area for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" IS NULL" % (school_level))))]
    
    # iterate through schools by current utilization in descending order (highest first) 
    for school_name, school_utilization in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k), reverse = True):
        if school_utilization > target_max_utilization:
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" = '%s'" % (school_name)))).next()
            #print "%s above at %d%%" % (school_name, school_utilization)
            
            owned_attendance_areas = attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))
            unowned_attendance_areas = attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" != '%s' OR \"%s\" IS NULL" % (school_level, school_name, school_level))))
            border_attendance_areas = {}
            
            # find attendance areas touching other (or unassigned) districts
            for owned_attendance_area in owned_attendance_areas:
                if owned_attendance_area['PLAN_ID'] not in home_areas.values():
                    #print owned_attendance_area['PLAN_ID']
                    for unowned_attendance_area in unowned_attendance_areas:
                        #print unowned_attendance_area['PLAN_ID']
                        if owned_attendance_area.geometry().touches(unowned_attendance_area.geometry()):
                            border_attendance_areas[owned_attendance_area] = distance_area.measureLine(school.geometry().asPoint(), owned_attendance_area.geometry().centroid().asPoint())
                            break

            # iterate through border attendance areas by distance in descending order (farthest first)
            for attendance_area, distance in sorted(border_attendance_areas.iteritems(), key = lambda (k,v): (v,k), reverse = True):
                population = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                new_population = school_populations[school_level][school_name] - population
                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                
                if new_utilization >= target_min_utilization:
                    #print "Planning to unassign %d (pop %d) from %s (%d%% -> %d%%)" % (attendance_area['PLAN_ID'], population, school_name, school_utilizations[school_level][school_name], new_utilization)
                    school_populations[school_level][school_name] = new_population
                    school_utilizations[school_level][school_name] = new_utilization
                    attendance_areas_to_update[attendance_area['PLAN_ID']] = NULL
                    null_attendance_areas.append(attendance_area)

                    if new_utilization <= target_max_utilization:
                        print "---------------------- finished with %s" % (school_name)
                        break
   
    # iterate through schools by current utilization in ascending order (lowest first) 
    for school_name, school_utilization in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k)):
        if school_utilization < target_min_utilization:
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" = '%s'" % (school_name)))).next()
            #print "%s below at %d%%" % (school_name, school_utilization)
            owned_attendance_areas = attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))
            
            # find attendance areas touching current district area          
            neighboring_attendance_areas = {}
            for null_attendance_area in null_attendance_areas:
                #other_attendance_area = attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"PLAN_ID\" = '%s'" % (plan_id)))).next()
                for attendance_area in owned_attendance_areas:
                    if null_attendance_area.geometry().touches(attendance_area.geometry()):
                        neighboring_attendance_areas[null_attendance_area] = distance_area.measureLine(school.geometry().asPoint(), null_attendance_area.geometry().centroid().asPoint())
                        break
            
            # iterate through neighboring attendance areas by distance in ascending order (closest first)
            for attendance_area, distance in sorted(neighboring_attendance_areas.iteritems(), key = lambda (k,v): (v,k)):
                population = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                new_population = school_populations[school_level][school_name] + population
                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                
                if new_utilization <= target_max_utilization:
                    #print "Planning to update %d (pop %d) to %s (%d%% -> %d%%)" % (attendance_area['PLAN_ID'], population, school_name, school_utilizations[school_level][school_name], new_utilization)
                    school_populations[school_level][school_name] = new_population
                    school_utilizations[school_level][school_name] = new_utilization
                    attendance_areas_to_update[attendance_area['PLAN_ID']] = school_name
                    null_attendance_areas.remove(attendance_area)
                                     
                    if new_utilization >= target_min_utilization:
                        print "---------------------- finished with %s" % (school_name)
                        break
                    
    # iterate through schools by current utilization in ascending order (lowest first) 
    for school_name, school_utilization in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k)):
        if school_utilization < target_max_utilization:
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" = '%s'" % (school_name)))).next()
            #print "%s at %d%% (%d null left)" % (school_name, school_utilization, len(null_attendance_areas))
            owned_attendance_areas = [attendance_area for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))]
            
            # find attendance areas touching current district area          
            neighboring_attendance_areas = {}
            for null_attendance_area in null_attendance_areas:
                #other_attendance_area = attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"PLAN_ID\" = '%s'" % (plan_id)))).next()
                for attendance_area in owned_attendance_areas:
                    if null_attendance_area.geometry().touches(attendance_area.geometry()):
                        neighboring_attendance_areas[null_attendance_area] = distance_area.measureLine(school.geometry().asPoint(), null_attendance_area.geometry().centroid().asPoint())
                        break
            
            # iterate through neighboring attendance areas by distance in ascending order (closest first)
            for attendance_area, distance in sorted(neighboring_attendance_areas.iteritems(), key = lambda (k,v): (v,k)):
                population = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                new_population = school_populations[school_level][school_name] + population
                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                
                if new_utilization <= target_max_utilization:
                    #print "Planning to update %d (pop %d) to %s (%d%% -> %d%%)" % (attendance_area['PLAN_ID'], population, school_name, school_utilizations[school_level][school_name], new_utilization)
                    school_populations[school_level][school_name] = new_population
                    school_utilizations[school_level][school_name] = new_utilization
                    attendance_areas_to_update[attendance_area['PLAN_ID']] = school_name
                    null_attendance_areas.remove(attendance_area)
                    
    attendance_areas_layer.startEditing()
         
    for attendance_area in attendance_areas_layer.getFeatures():
        if attendance_area['PLAN_ID'] in list(attendance_areas_to_update.keys()):
            attendance_area[school_level] = attendance_areas_to_update[attendance_area['PLAN_ID']]
            attendance_areas_layer.updateFeature(attendance_area)
             
    attendance_areas_layer.commitChanges()
    
#     assigned_attendance_areas = {}
#     for attendance_area in attendance_areas_layer.getFeatures():
#         if attendance_area not in null_attendance_areas:
#             plan_id = attendance_area['PLAN_ID']
#             if plan_id in attendance_areas_to_update:
#                 assigned_attendance_areas[attendance_area] = attendance_areas_to_update[plan_id]
#             else:
#                 assigned_attendance_areas[attendance_area] = attendance_area[school_level]
#     
    null_attendance_areas = [attendance_area for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" IS NULL" % (school_level))))]
    
    # iterate over unassigned districts
    while len(null_attendance_areas) > 0:
        starting_length = len(null_attendance_areas)
        for null_attendance_area in null_attendance_areas:
            adjacent_schools = {}
                
            for attendance_area in attendance_areas_layer.getFeatures(request = QgsFeatureRequest(QgsExpression("\"%s\" IS NOT NULL" % (school_level)))):
                if null_attendance_area.geometry().touches(attendance_area.geometry()):
                    adjacent_schools[attendance_area[school_level]] = school_utilizations[school_level][attendance_area[school_level]]
            
            if len(adjacent_schools) > 0:
                school_name = sorted(adjacent_schools.iteritems(), key = lambda (k,v): (v,k))[0][0]
                population = attendance_area_populations[school_level][null_attendance_area['PLAN_ID']]
                new_population = school_populations[school_level][school_name] + population
                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                    
                if True:#new_utilization <= target_max_utilization:
                    #print "Adding %d (pop %d) to %s (%d%% -> %d%%)" % (null_attendance_area['PLAN_ID'], population, school_name, school_utilizations[school_level][school_name], new_utilization)
                    school_populations[school_level][school_name] = new_population
                    school_utilizations[school_level][school_name] = new_utilization
                    attendance_areas_to_update[null_attendance_area['PLAN_ID']] = school_name
                    null_attendance_areas.remove(null_attendance_area)
        if len(null_attendance_areas) == starting_length:
            break
        else:
            attendance_areas_layer.startEditing()
                 
            for attendance_area in attendance_areas_layer.getFeatures():
                if attendance_area['PLAN_ID'] in list(attendance_areas_to_update.keys()):
                    attendance_area[school_level] = attendance_areas_to_update[attendance_area['PLAN_ID']]
                    attendance_areas_layer.updateFeature(attendance_area)
                     
            attendance_areas_layer.commitChanges()
                    
    # for every school outside target utilization, offload attendance areas to neighboring schools with less utilization
    #schools_below_target = {}
    #schools_above_target = {}
    school_populations_prj = school_populations[school_level].copy()
    school_utilizations_prj = school_utilizations[school_level].copy()
     
    attendance_areas_to_update = {}
    attendance_areas_prj = {}
    for attendance_area in attendance_areas_layer.getFeatures():
        attendance_areas_prj[attendance_area['PLAN_ID']] = {}
        attendance_areas_prj[attendance_area['PLAN_ID']]['attendance_area'] = attendance_area
        attendance_areas_prj[attendance_area['PLAN_ID']]['assigned_school'] = attendance_area[school_level]
    
    for counter in range(0, num_iterations):
        bar_counter = bar_counter + 1
        bar.update(bar_counter)
        voronoi_polygons = {}
         
        for voronoi_polygon in voronoi_layer.getFeatures():
            voronoi_polygons[voronoi_polygon] = school_utilizations_prj[voronoi_polygon['Name']]
             
        # iterate through schools by current utilization in ascending order (lowest first) 
        for voronoi_polygon, _ in sorted(voronoi_polygons.iteritems(), key = lambda (k,v): (v,k)):
            school_name = voronoi_polygon['Name']
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" != '%s'" % (school_name)))).next()
            school_utilization = school_utilizations_prj[school_name]
            # check if utilization is outside target
            if school_utilization < target_min_utilization or school_utilization > target_max_utilization :
                #print "Correcting %s (%d%%)" % (school_name, school_utilization)
                # construct dictionary for sorting neighboring schools by utilization
                neighboring_schools = {}
                for other_voronoi_polygon in voronoi_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" != '%s'" % (school_name)))):
                    if voronoi_polygon.geometry().touches(other_voronoi_polygon.geometry()):
                        neighboring_schools[other_voronoi_polygon['Name']] = school_utilizations[school_level][other_voronoi_polygon['Name']]
                 
                if school_utilization > target_max_utilization:
                    #schools_above_target[school_name] = school_utilizations[school_level][school_name]
                    #print "%d%% above target (%s)" % (school_utilization, school_name)
                    attendance_areas_to_give = {}
                    for plan_id, area_data in attendance_areas_prj.iteritems():
                        attendance_area = area_data['attendance_area']
                        assigned_school = area_data['assigned_school']
                        
                        if assigned_school == school_name and plan_id not in home_areas.values():
                            attendance_areas_to_give[attendance_area['PLAN_ID']] = distance_area.measureLine(school.geometry().asPoint(), attendance_area.geometry().centroid().asPoint())
                            #attendance_areas_to_give[attendance_area['PLAN_ID']] = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                                 
                    # iterate through neighboring schools by utilization in ascending order (lowest first)
                    for other_school_name, _ in sorted(neighboring_schools.iteritems(), key = lambda (k,v): (v,k)):
                        in_target = False
                        # iterate through shared attendance areas by distance in descending order (farthest first)
                        for plan_id, distance in sorted(attendance_areas_to_give.iteritems(), key = lambda (k,v): (v,k), reverse = True):
                            population = attendance_area_populations[school_level][plan_id]
                            assigned_school = attendance_areas_prj[plan_id]['assigned_school']
                             
                            # check if current attendance area belongs to the current school 
                            if assigned_school == school_name:
                                new_population = school_populations_prj[school_name] - population
                                other_new_population = school_populations_prj[other_school_name] + population
                                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                                other_new_utilization = float(other_new_population) * 100 / school_capacities[school_level][other_school_name]
                                 
                                if True:#new_utilization >= other_new_utilization:#new_utilization <= target_max_utilization:
                                    #print "Planning to update %d (pop %d) from %s (%d%% -> %d%%) to %s (%d%% -> %d%%)" % (plan_id, population, school_name, school_utilizations_prj[school_name], new_utilization, other_school_name, school_utilizations_prj[other_school_name], other_new_utilization)
                                    school_populations_prj[school_name] = new_population
                                    school_populations_prj[other_school_name] = other_new_population
                                    school_utilizations_prj[school_name] = new_utilization
                                    school_utilizations_prj[other_school_name] = other_new_utilization
                                    attendance_areas_to_update[plan_id] = other_school_name
                                    attendance_areas_prj[plan_id]['assigned_school'] = other_school_name
                                     
                                    if school_utilizations_prj[school_name] <= target_max_utilization:
                                        in_target = True
                                        break
                        if in_target:
                            #print 'done with %s' % (school_name)
                            break
                elif school_utilization < target_min_utilization:
                    #schools_below_target[school_name] = school_utilizations[school_level][school_name]
                    #print "%d%% below target (%s)" % (school_utilization, school_name)
                    attendance_areas_to_take = {}
                    for plan_id, area_data in attendance_areas_prj.iteritems():
                        attendance_area = area_data['attendance_area']
                        assigned_school = area_data['assigned_school']
                         
                        if assigned_school != school_name:
                            for plan_id, other_area_data in attendance_areas_prj.iteritems():
                                if other_area_data['assigned_school'] == school_name:
                                    if attendance_area.geometry().touches(other_area_data['attendance_area'].geometry()):
                                        #attendance_areas_to_take[attendance_area['PLAN_ID']] = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                                        attendance_areas_to_take[attendance_area['PLAN_ID']] = distance_area.measureLine(school.geometry().asPoint(), attendance_area.geometry().centroid().asPoint())
                                        break
                             
                    # iterate through neighboring schools by utilization in descending order (highest first))                    for other_school_name, _ in sorted(neighboring_schools.iteritems(), key = lambda (k,v): (v,k), reverse = True):
                        in_target = False
                        # iterate through shared attendance areas by distance in ascending order (closest first)
                        for plan_id, distance in sorted(attendance_areas_to_take.iteritems(), key = lambda (k,v): (v,k)):
                            population = attendance_area_populations[school_level][plan_id]
                            assigned_school = attendance_areas_prj[plan_id]['assigned_school']
                             
                            # check if current attendance area belongs to the other school 
                            if assigned_school == other_school_name:
                                new_population = school_populations_prj[school_name] + population
                                other_new_population = school_populations_prj[other_school_name] - population
                                new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                                other_new_utilization = float(other_new_population) * 100 / school_capacities[school_level][other_school_name]
                                 
                                if True:#new_utilization <= other_new_utilization:#other_new_utilization <= target_max_utilization:
                                    #print "Planning to update %d (pop %d) from %s (%d%% -> %d%%) to %s (%d%% -> %d%%)" % (plan_id, population, other_school_name, school_utilizations_prj[other_school_name], other_new_utilization, school_name, school_utilizations_prj[school_name], new_utilization)
                                    school_populations_prj[school_name] = new_population
                                    school_populations_prj[other_school_name] = other_new_population
                                    school_utilizations_prj[school_name] = new_utilization
                                    school_utilizations_prj[other_school_name] = other_new_utilization
                                    attendance_areas_to_update[plan_id] = school_name
                                    attendance_areas_prj[plan_id]['assigned_school'] = school_name
                                     
                                    if school_utilizations_prj[school_name] >= target_min_utilization:
                                        in_target = True
                                        break
                        if in_target:
                            #print 'done with %s' % (school_name)
                            break
         
    attendance_areas_layer.startEditing()
         
    for attendance_area in attendance_areas_layer.getFeatures():
        if attendance_area['PLAN_ID'] in list(attendance_areas_to_update.keys()):
            attendance_area[school_level] = attendance_areas_to_update[attendance_area['PLAN_ID']]
            attendance_areas_layer.updateFeature(attendance_area)
             
    attendance_areas_layer.commitChanges()
     
    school_utilizations[school_level] = school_utilizations_prj
    school_populations[school_level] = school_populations_prj
 
print '\n'
 
print "iterations: %d" % (num_iterations)
 
current_avg_utilization = [sum([utilization for school_name, utilization in current_school_utilizations[school_level].iteritems()]) for school_level in school_levels]
avg_utilization = [sum([utilization for school_name, utilization in school_utilizations[school_level].iteritems()]) for school_level in school_levels]
 
for school_level in school_levels:
    index = school_levels.index(school_level)
    #print "\n%d%% -> %d%% average utilization in %s school districts" % (current_avg_utilization[index] / [41, 20, 12][index], avg_utilization[index] / [41, 20, 12][index], school_level)
    for school_name in school_utilizations[school_level].keys():
        #print "%d%% -> %d%% %s" % (current_school_utilizations[school_level][school_name], school_utilizations[school_level][school_name], school_name)
        print "%s, %d" % (school_name, school_utilizations[school_level][school_name])

#_writer = QgsVectorFileWriter.writeAsVectorFormat(attendance_areas_layer, os.path.join(output_dir, 'attendance_areas.shp'), "utf-8", QgsCoordinateReferenceSystem('epsg:4326'))
#_writer = QgsVectorFileWriter.writeAsVectorFormat(thiessen_layer, os.path.join(output_dir, 'attendance_areas_thiessen.shp'), "utf-8", QgsCoordinateReferenceSystem('epsg:4326'))

# close QGIS application providers
qgs.exitQgis()

print "done"
