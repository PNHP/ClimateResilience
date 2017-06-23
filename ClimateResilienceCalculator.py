#-------------------------------------------------------------------------------
# Name:        Climate Resiliency Calculator
# Purpose:     Returns percentage climate resiliency categories and tiers within
#              selected properties
# Author:      Molly Moore
# Created:     2017-06-22
# Updated:
#
# To Do List/Future ideas:
#
#-------------------------------------------------------------------------------

# import system modules
import arcpy, os, datetime
from arcpy import env
from arcpy.sa import *

# establish environmental settings
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.env.workspace = r'W:\Conservation_Science\Science\ClimateChangeWPC\ClimateResilienceCalculator\PropertyResilienceOutput.gdb'

# define parameters
properties = arcpy.GetParameterAsText(0)
climate = arcpy.GetParameterAsText(1)
outGDB = arcpy.GetParameterAsText(2)
# permanent location of template? can change if needed.
template = r'W:\Conservation_Science\Science\ClimateChangeWPC\climateResilienceCalculator\ResilienceCalculator.gdb\GeophysicalSettings_Template'

# dissolve selected properties with same name
properties_dissolve = arcpy.Dissolve_management(properties, "properties_dissolve", "TRACT_NAME")
# create list of selected property names
with arcpy.da.SearchCursor(properties, "TRACT_NAME") as cursor:
    tract_names = sorted({row[0] for row in cursor})
tract_names = [str(x) for x in tract_names]

for name in tract_names:
    # create feature layer of each tract in a loop
    tract = arcpy.MakeFeatureLayer_management(properties_dissolve, "tract", '"TRACT_NAME" = ' + "'%s'" %name)

    # eliminate spaces and special characters from tract name to use in geoprocessing tools
    n = ''.join(x for x in name if x.isalnum())

    # tabulate area
    tab_area = TabulateArea(tract, "TRACT_NAME", climate, "Tier_Resilience", "tab_area")

    # create list of fields to transpose
    all_fields = [f.name for f in arcpy.ListFields(tab_area)]
    exclude_fields = ["TRACT_NAME", "OID", "OBJECTID"]
    transpose_fields = [x for x in all_fields if x not in exclude_fields]
    transpose_fields = [str(x) for x in transpose_fields]
    new_names = [x[-2:] for x in transpose_fields]
    transpose_fields = [transpose_fields[i]+" "+new_names[i] for i in xrange(len(transpose_fields))]

    # transpose fields
    transpose = arcpy.TransposeFields_management(tab_area, ';'.join(transpose_fields), "transpose", "Tier_Resilience", "Area", "TRACT_NAME")

    # get total area
    with arcpy.da.SearchCursor(transpose, "Area") as cursor:
            summed_total = 0
            for row in cursor:
                summed_total = summed_total + int(row[0])

    # convert areas to percentage and round to nearest 1%
    with arcpy.da.UpdateCursor(transpose, "Area") as cursor:
            for row in cursor:
                row[0] = int(row[0])/float(summed_total)*100
                row[0] = int(5*round(float(row[0]/5)))
                cursor.updateRow(row)

    # create copy of template
    joinTable = arcpy.TableToTable_conversion(template, "in_memory", "joinTable")

    # join area field to template table
    joinTable = arcpy.JoinField_management(joinTable, "Tier_Resilience", transpose, "Tier_Resilience", "Area")

    # fill null values with 0 and add % sign to all values
    with arcpy.da.UpdateCursor(joinTable, "Area") as cursor:
        for row in cursor:
            if row[0] is None:
                row[0] = 0
                cursor.updateRow(row)
            row[0] = str(row[0]) + '%'
            cursor.updateRow(row)

    # pivot table for final format
    arcpy.PivotTable_management(joinTable, "Resilience_Score", "Tier", "Area", os.path.join(outGDB, n + "_" + "climate_resilience"))

# delete temporary feature classes
deleteFC = [os.path.join(env.workspace, "properties_dissolve"), os.path.join(env.workspace, "tab_area"), os.path.join(env.workspace, "transpose")]

for FC in deleteFC:
    arcpy.Delete_management(FC)




