'''
Created on Nov 6, 2017

Given input data (attendance area polygons, school capacities, school points, and attendance area enrollment) for each school level, 
this script will attempt to assign attendance areas in a balanced manner. 

The main loop is split into two phases: initial assignment and rebalancing. 

The current iteration of this script (with only one iteration) does not create islands, 
but also does not completely balance school capacities or always fall within target limits.

@author: Zach
'''

import os
import pandas
import progressbar

# import from /apps/qgis/python/
from qgis.core import QgsApplication, QgsVectorLayer, QgsFeatureRequest, QgsExpression, QgsField, QgsDistanceArea, QgsCoordinateReferenceSystem, NULL
from PyQt4.QtCore import QVariant

# initialize QGIS application providers
qgs = QgsApplication([], True)
qgs.setPrefixPath(r'A:\OSGeo4W64\apps\qgis', True)
qgs.initQgis()

# import QGIS processing toolbox
from processing.core.Processing import Processing
Processing.initialize()
from processing.tools import general

# create a QGIS measure object
distance_area = QgsDistanceArea()
crs = QgsCoordinateReferenceSystem()
crs.createFromSrsId(3452) # EPSG:4326
distance_area.setSourceCrs(crs)
distance_area.setEllipsoidalMode(True)
distance_area.setEllipsoid('WGS84')

# define number of iterations of rebalancing phase (more iterations makes more islands)
num_iterations = 1

# define school levels
school_levels = ['elem', 'midd', 'high']

# define output directory
output_dir = r"B:\Workspaces\GIS\GEOG653\final_project\output"

# define filenames
attendance_areas_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\MPIA\FS17_COMpolys.shp"
school_capacities_filenames = {
    'elem': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_elem.csv",
    'midd': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_midd.csv",
    'high': r"B:\Workspaces\GIS\GEOG653\final_project\data\capacities_high.csv"
    }
schools_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\schools.shp"
enrollment_filename = r"B:\Workspaces\GIS\GEOG653\final_project\data\PPPROJ17-EnrollmentHousing.xlsx"

# load vector data
if not os.path.exists(os.path.join(output_dir, "schools.shp")):
    general.runalg("qgis:reprojectlayer", schools_filename, "epsg:4326", os.path.join(output_dir, "schools.shp"))
general.runalg("qgis:splitvectorlayer", QgsVectorLayer(os.path.join(output_dir, "schools.shp"), 'schools', 'ogr'), "Level", output_dir)
schools_layers = {}
for school_level in school_levels:
    schools_layers[school_level] = QgsVectorLayer(os.path.join(output_dir, "schools.shp_Level_%s.shp" % (school_level)), 'schools_%s' % (school_level), 'ogr')

# reproject layerto EPSG 4326 for processing
general.runalg("qgis:reprojectlayer", attendance_areas_filename, "epsg:4326", os.path.join(output_dir, "attendance_areas.shp"))
attendance_areas_layer = QgsVectorLayer(os.path.join(output_dir, "attendance_areas.shp"), 'attendance_areas', 'ogr')

# create progress bar
bar = progressbar.ProgressBar(max_value=len(school_levels) * (num_iterations + 3))
bar_counter = 0
bar.update(bar_counter)

# get population fields per grade level
enrollment_dataframe = pandas.read_excel(enrollment_filename, sheet_name = 'PPPROJ17', header = 1, skiprows = 0)
enrollment_population_fields = {
    'elem': ['GR0_POP', 'GR1_POP', 'GR2_POP', 'GR3_POP', 'GR4_POP', 'GR5_POP'],#['GR0_POP', 'ESPROJ0'],
    'midd': ['GR6_POP', 'GR7_POP', 'GR8_POP'],#['MSPROJ0'],
    'high': ['GR9_POP', 'GR10_POP', 'GR11_POP', 'GR12_POP']#['HSPROJ0']
    }

attendance_area_populations = {}

# get sum of populations per school level
for school_level in school_levels:
    attendance_area_populations[school_level] = dict(zip(enrollment_dataframe['PLAN_ID'], sum([enrollment_dataframe[population_field] for population_field in enrollment_population_fields[school_level]])))

# read school capacities
school_capacities = {}

for school_level in school_levels:
    school_capacities_dataframe = pandas.read_csv(school_capacities_filenames[school_level])
    school_capacities[school_level] = dict(zip(school_capacities_dataframe['school'], school_capacities_dataframe['capacity']))
    
# define target minimum and maximum utilization per school
target_min_utilization = 90
target_max_utilization = 110

# create dictionaries for populations
school_populations = {}
current_school_populations = {}

# create dictionaries for utilizations and thiessen polygons
school_utilizations = {}
current_school_utilizations = {}
thiessen_layer = {}

# create dictionary for any manual attendance area assignments
manual_changes = {}
manual_changes['elem'] = {}
#     294: "Bushy Park ES",
#     85: "Ilchester ES",
#     1298: "Bellows Spring ES",
#     2077: "Bellows Spring ES",
#     80: "Bellows Spring ES",
#     1080: "Bellows Spring ES"
# }
manual_changes['midd'] = {}
manual_changes['high'] = {}

# iterate over school levels (main loop)
for school_level in school_levels:
    # update progress bar
    bar_counter = bar_counter + 1
    bar.update(bar_counter)
           
    if school_level == 'elem':
        school_level_key = 'ES_HOME'
    elif school_level == 'midd':
        school_level_key = 'MS_HOME'
    elif school_level == 'high':
        school_level_key = 'HS_HOME'
    
    schools_layer = schools_layers[school_level]
    schools = schools_layer.getFeatures()
    school_names = [school['Name'] for school in schools]
           
    # find current school utilizations by capacity
    current_school_populations[school_level] = {}
    current_school_utilizations[school_level] = {}
    for school_name in school_names:
        school_population = sum([attendance_area_populations[school_level][attendance_area['PLAN_ID']] for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level_key, school_name))))])
        current_school_populations[school_level][school_name] = school_population
        current_school_utilizations[school_level][school_name] = school_population * 100 / school_capacities[school_level][school_name]
     
    # calculate Voronoi (Thiessen) polygons if it does not exist
    voronoi_filename = os.path.join(output_dir, 'voronoi_%s.shp' % (school_level))
    if not os.path.exists(voronoi_filename):
        voronoi_temp_filename = os.path.join(output_dir, 'voronoi_%s_temp.shp' % (school_level))
        general.runalg("saga:thiessenpolygons", schools_layer, 0.2, voronoi_temp_filename)
        general.runalg("qgis:clip", voronoi_temp_filename, os.path.join(output_dir, "attendance_areas.shp"), voronoi_filename)
    voronoi_layer = QgsVectorLayer(voronoi_filename, 'voronoi_%s' % (school_level), 'ogr')

    # update progress bar
    bar_counter = bar_counter + 1
    bar.update(bar_counter)
    
    # add new field
    if school_level not in [field.name() for field in attendance_areas_layer.fields()]:
        attendance_areas_layer.dataProvider().addAttributes([QgsField(school_level, QVariant.String)])
        attendance_areas_layer.updateFields()
        
    # start applying changes
    attendance_areas_layer.startEditing()
    
    # find attendance areas within voronoi polygons
    for attendance_area in attendance_areas_layer.getFeatures():
        for voronoi_polygon in voronoi_layer.getFeatures():
            if attendance_area.geometry().within(voronoi_polygon.geometry()):
                attendance_area[school_level] = voronoi_polygon['Name']
                attendance_areas_layer.updateFeature(attendance_area)
                break
    
    # define and populate attendance areas where schools physically reside (do not give away home area)
    home_areas = {}
    
    for school in schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Level\" = '%s'" % (school_level)))):
        for attendance_area in attendance_areas_layer.getFeatures():
            if school.geometry().within(attendance_area.geometry()):
                home_areas[school['Name']] = attendance_area['PLAN_ID']
                attendance_area[school_level] = school['Name']
                attendance_areas_layer.updateFeature(attendance_area)
    
    # commit applied changes
    attendance_areas_layer.commitChanges()
    
    # update progress bar
    bar_counter = bar_counter + 1
    bar.update(bar_counter)
             
    # find school utilizations by capacity
    school_populations[school_level] = {}
    school_utilizations[school_level] = {}
    for school_name in school_names:
        school_population = sum([attendance_area_populations[school_level][attendance_area['PLAN_ID']] for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))])
        school_populations[school_level][school_name] = school_population
        school_utilizations[school_level][school_name] = school_population * 100 / school_capacities[school_level][school_name]
    
    # ----------------------------------------------------- initial assignment phase ------------------------------------------------------------
    
    # create dictionary to hold changes to apply
    attendance_areas_to_update = {}
    
    # find all attendance areas without a school assignment
    null_attendance_areas = [attendance_area for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" IS NULL" % (school_level))))]
    
    # iterate through schools by current utilization in descending order (highest first)
    for school_name, school_utilization in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k), reverse = True):
        if school_utilization > target_max_utilization:
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" = '%s'" % (school_name)))).next()
            #print "%s above at %d%%" % (school_name, school_utilization)
            
            # get attendance areas assigned and not assigned to the current school, as well as those bordering its current area
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
                        #print "---------------------- finished with %s" % (school_name)
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
                        #print "---------------------- finished with %s" % (school_name)
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
                    
    # start applying queue of changes
    attendance_areas_layer.startEditing()
         
    for attendance_area in attendance_areas_layer.getFeatures():
        if attendance_area['PLAN_ID'] in list(attendance_areas_to_update.keys()):
            attendance_area[school_level] = attendance_areas_to_update[attendance_area['PLAN_ID']]
            attendance_areas_layer.updateFeature(attendance_area)
    
    # commit changes         
    attendance_areas_layer.commitChanges()
    
    # ------------------------------------------------------------ rebalancing phase ----------------------------------------------
    
    # find all attendance areas still lacking a school assignment
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
     
    # create dictionary of attendance areas to update with new assignments
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
         
        # iterate through schools by current utilization in ascending order (lowest first) 
        for school_name, _ in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k), reverse = True):
            school = schools_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" != '%s'" % (school_name)))).next()
            school_utilization = school_utilizations_prj[school_name]
            # check if utilization is outside target
            if school_utilization < target_min_utilization or school_utilization > target_max_utilization:
                #print "Correcting %s (%d%%)" % (school_name, school_utilization)
                
                owned_attendance_areas = []
                unowned_attendance_areas = []
                for plan_id, area_data in attendance_areas_prj.iteritems():
                    if area_data['assigned_school'] == school_name:
                        owned_attendance_areas.append(area_data['attendance_area'])
                    else:
                        unowned_attendance_areas.append(area_data['attendance_area'])

                # find schools adjacent to current school
                adjacent_schools = {}
                for owned_attendance_area in owned_attendance_areas:
                    for unowned_attendance_area in unowned_attendance_areas:
                        if owned_attendance_area.geometry().touches(unowned_attendance_area.geometry()):
                            adjacent_schools[unowned_attendance_area[school_level]] = school_utilizations[school_level][unowned_attendance_area[school_level]]

                
#                 # construct dictionary for sorting neighboring schools by utilization
#                 neighboring_schools = {}
#                 for other_voronoi_polygon in voronoi_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"Name\" != '%s'" % (school_name)))):
#                     if voronoi_polygon.geometry().touches(other_voronoi_polygon.geometry()):
#                         neighboring_schools[other_voronoi_polygon['Name']] = school_utilizations[school_level][other_voronoi_polygon['Name']]
                 
                if school_utilization > target_max_utilization:
                    #schools_above_target[school_name] = school_utilizations[school_level][school_name]
                    #print "%d%% above target (%s)" % (school_utilization, school_name)
                    attendance_areas_to_give = {}
                    for owned_attendance_area in owned_attendance_areas:
                        attendance_areas_to_give[owned_attendance_area] = distance_area.measureLine(school.geometry().asPoint(), owned_attendance_area.geometry().centroid().asPoint())
                        #attendance_areas_to_give[attendance_area['PLAN_ID']] = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                                 
                    # iterate through neighboring schools by utilization in ascending order (lowest first)
                    for other_school_name, _ in sorted(adjacent_schools.iteritems(), key = lambda (k,v): (v,k)):
                        other_owned_attendance_areas = []
                        for plan_id, area_data in attendance_areas_prj.iteritems():
                            if area_data['assigned_school'] == other_school_name:
                                other_owned_attendance_areas.append(area_data['attendance_area'])
                        in_target = False
                        # iterate through shared attendance areas by distance in descending order (farthest first)
                        for attendance_area, distance in sorted(attendance_areas_to_give.iteritems(), key = lambda (k,v): (v,k), reverse = True):
                            touching_other_school = False
                            for other_attendance_area in other_owned_attendance_areas:
                                if attendance_area.geometry().touches(other_attendance_area.geometry()):
                                    touching_other_school = True
                                    break
                            
                            if touching_other_school:
                                population = attendance_area_populations[school_level][plan_id]
                                assigned_school = attendance_areas_prj[plan_id]['assigned_school']
                                 
                                # check if current attendance area belongs to the current school 
                                if assigned_school == school_name:
                                    new_population = school_populations_prj[school_name] - population
                                    other_new_population = school_populations_prj[other_school_name] + population
                                    new_utilization = float(new_population) * 100 / school_capacities[school_level][school_name]
                                    other_new_utilization = float(other_new_population) * 100 / school_capacities[school_level][other_school_name]
                                     
                                    if True:#other_new_utilization <= target_max_utilization:
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
                    for owned_attendance_area in owned_attendance_areas:
                        for unowned_attendance_area in unowned_attendance_areas:
                            if unowned_attendance_area.geometry().touches(owned_attendance_area.geometry()):
                                #attendance_areas_to_take[attendance_area['PLAN_ID']] = attendance_area_populations[school_level][attendance_area['PLAN_ID']]
                                attendance_areas_to_take[unowned_attendance_area['PLAN_ID']] = distance_area.measureLine(school.geometry().asPoint(), unowned_attendance_area.geometry().centroid().asPoint())
                                break
                             
                    # iterate through neighboring schools by utilization in descending order (highest first))                    for other_school_name, _ in sorted(adjacent_schools.iteritems(), key = lambda (k,v): (v,k), reverse = True):
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
            
    for plan_id, school_name in manual_changes[school_level].iteritems():
        attendance_areas_to_update[plan_id] = school_name
    
    # start applying changes
    attendance_areas_layer.startEditing()
         
    for attendance_area in attendance_areas_layer.getFeatures():
        if attendance_area['PLAN_ID'] in list(attendance_areas_to_update.keys()):
            attendance_area[school_level] = attendance_areas_to_update[attendance_area['PLAN_ID']]
            attendance_areas_layer.updateFeature(attendance_area)
    
    # commit changes
    attendance_areas_layer.commitChanges()
     
    school_utilizations[school_level] = school_utilizations_prj
    school_populations[school_level] = school_populations_prj
    
    # find school utilizations by capacity
    for school_name in school_names:
        school_population = sum([attendance_area_populations[school_level][attendance_area['PLAN_ID']] for attendance_area in attendance_areas_layer.getFeatures(request=QgsFeatureRequest(QgsExpression("\"%s\" = '%s'" % (school_level, school_name))))])
        school_populations[school_level][school_name] = school_population
        school_utilizations[school_level][school_name] = school_population * 100 / school_capacities[school_level][school_name]
 
print '\n'
 
print "iterations: %d" % (num_iterations)
 
print 'school_name, current_school_population, new_school_population, school_capacity, current_school_utilization, new_school_utilization'
 
for school_level in school_levels:
    for school_name, school_utilization in sorted(school_utilizations[school_level].iteritems(), key = lambda (k,v): (v,k), reverse = True):
        print "%s, %d, %d, %d, %d, %d" % (school_name, current_school_populations[school_level][school_name], school_populations[school_level][school_name], school_capacities[school_level][school_name], current_school_utilizations[school_level][school_name], school_utilization)

# close QGIS application providers
qgs.exitQgis()

for school_level in school_levels:
    os.remove(os.path.join(output_dir, 'schools.shp_Level_%s.shp' % (school_level)))

print "done"
