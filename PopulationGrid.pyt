# -*- coding: utf-8 -*-
import arcpy
class Toolbox:
    def __init__(self):
        self.label = "Population Grid"
        self.alias = "POGCZ"

        # List of tool classes associated with this toolbox
        self.tools = [NightState, DailyState]


class NightState:
    def __init__(self):
        self.label = "Night State of Population"
        self.description = "A tool for generating of the Night State variant of the population grid in raster or vector form based on user-defined criteria.\nPotential input data suitable for the Czech environment can be the \"Budovy s číslem domu a vchody\" layers and its data on the permanent or habitual residence of persons, including foreigners, as part of the Register of Census Districts and Buildings (Registr sčítacích obvodů a budov; abbreviated as RSO), which is administered and provided by the Czech Statistical Office."

    def getParameterInfo(self):
        """ PARAMETERS DEFINITION """

        """ Input Feature Layer """
        param_PopulationFeatureLayer = arcpy.Parameter(displayName="Population Layer (Point Layer)",
                            name="population_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Required",
                            direction="Input")
        # Only for point data
        param_PopulationFeatureLayer.filter.list = ["Point"]


        """ Population Count Field """
        param_PopulationCountField = arcpy.Parameter(displayName="Population Count (Field)",
                            name="population_count_field",
                            datatype="Field",
                            parameterType="Required",
                            direction="Input")
        # Show a list of PopulationFeatureLayer's attributes
        param_PopulationCountField.parameterDependencies = [param_PopulationFeatureLayer.name]


        """ Target Area Polygon """
        param_TargetAreaPolygon = arcpy.Parameter(displayName="Target Area (Polygon Layer)",
                            name="target_area_polygon",
                            datatype="GPFeatureLayer",
                            parameterType="Required",
                            direction="Input")
        # Only for polygon data
        param_TargetAreaPolygon.filter.list = ["Polygon"]

        """ Enable Custom Grid Option """
        param_CustomGrid_Enable = arcpy.Parameter(displayName="Enable Custom Grid Layer",
                            name="enable_custom_grid_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")      


        """ Custom Grid Layer """
        param_CustomGridLayer = arcpy.Parameter(displayName="Custom Grid Layer (Polygon Layer)",
                            name="custom_grid_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for polygon data
        param_CustomGridLayer.filter.list = ["Polygon"]

        """ Grid Cell Size """
        param_GridCellSize = arcpy.Parameter(displayName="Grid Cell Size",
                            name="grid_cell_size",
                            datatype="GPArealUnit",
                            parameterType="Required",
                            direction="Input")
        # Default value (1 SqKm)
        param_GridCellSize.value = "1 SquareKilometers"


        """ Grid Shape Type """
        param_GridShapeType = arcpy.Parameter(displayName="Grid Cell Shape",
                            name="grid_shape_type",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Set a value list of grid shape types
        param_GridShapeType.filter.type = "ValueList"
        param_GridShapeType.filter.list = ["Square", "Triangle", "Hexagon", "Transverse Hexagon", "Diamond"]
        # Default value (0=Square)
        param_GridShapeType.value = param_GridShapeType.filter.list[0]


        """ Spatial Reference """
        param_SpatialReference = arcpy.Parameter(displayName="Spatial Reference",
                            name="spatial_reference",
                            datatype="GPSpatialReference",
                            parameterType="Required",
                            direction="Input")
        # Default value (5514=S-JTSK_Krovak_East_North)
        param_SpatialReference.values = arcpy.SpatialReference(5514)


        """ Output Geodatabase """
        param_Workspace = arcpy.Parameter(displayName="Output Geodatabase",
                            name="output_workspace",
                            datatype="DEWorkspace",
                            parameterType="Required",
                            direction="Input")
        # Allow to select Geodatabase path only
        param_Workspace.filter.list = ["Local Database"]


        """ Output Type """
        param_OutputType = arcpy.Parameter(displayName="Output Type",
                            name="output_type",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Set a value list of grid shape types
        param_OutputType.filter.type = "ValueList"
        param_OutputType.filter.list = ["Raster", "Vector"]
        # Default value (0=Raster)
        param_OutputType.values = param_OutputType.filter.list[0]


        """ Output Feature Class Name """
        param_OutputName = arcpy.Parameter(displayName="Output Name",
                            name="output_name",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Default output filename
        param_OutputName.value = "PopulationGrid_NightState"

        """ Active parameters array """
        params = [param_PopulationFeatureLayer, param_PopulationCountField, param_TargetAreaPolygon, 
                  param_CustomGrid_Enable, param_CustomGridLayer, param_GridCellSize,
                  param_GridShapeType, param_SpatialReference, param_Workspace, param_OutputType, param_OutputName]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modifying the values and properties of parameters before internal validation (when the parameter is changed)"""
        # Re-change Population Count Field value if altered Input Feature Layer
        if parameters[0].altered and not parameters[0].hasBeenValidated:
            parameters[1].value = ""

        # If the custom grid option checked, activate the custom grid layer field and deactivate parameter fields for generating a new grid
        if parameters[3].value:
            parameters[4].enabled = True
            parameters[5].enabled = False
            parameters[6].enabled = False
        else:
            parameters[4].enabled = False
            parameters[5].enabled = True
            parameters[6].enabled = True

        return

    def updateMessages(self, parameters):
        """Additional field check (invoked after changing the value in the corresponding field)"""
        Grid_Size = parameters[5].valueAsText
        if  Grid_Size is not None:   
                Grid_Size_value_raw,Grid_Size_unit=Grid_Size.split(" ")
                # Error message at zero/negative grid size value (Grid Cell Size parameter)
                if float(Grid_Size_value_raw.replace(',', '.')) <= 0:
                        parameters[5].setErrorMessage("Grid Cell size cannot be zero or negative!")

                # Disabling the use of Unknown unit in Grid Cell Size Areal Unit Field
                if str(Grid_Size_unit) == "Unknown":
                        parameters[5].setErrorMessage("The use of the \"Unknown\" unit is not allowed within this toolbox. Choose a different spatial unit.")

        # Function to check Input Feature Layer projection mismatch with defined Spatial Reference
        def layer_projection_mismatch(layer_param_index, layer_name, spref_field_index):
                if str(parameters[layer_param_index].valueAsText) != "" and arcpy.Exists(str(parameters[layer_param_index].valueAsText)):
                        SR_InputFeatureLayer = arcpy.Describe(str(parameters[layer_param_index].valueAsText)).spatialReference.name
                        SR_Field = arcpy.SpatialReference()
                        SR_Field.loadFromString(parameters[spref_field_index].valueAsText)
                        if SR_InputFeatureLayer != SR_Field.name:
                                parameters[layer_param_index].setErrorMessage(str(layer_name) + "'s projection mismatch with defined Spatial Reference.")
        # Input Layers projection mismatch checks
        layer_projection_mismatch(0, "Point Population Layer", 7)
        layer_projection_mismatch(2, "Target Area Polygon", 7)
        layer_projection_mismatch(4, "Custom Grid Layer", 7)
        
        # Check Population Count Field type
        if arcpy.Exists(str(parameters[0].valueAsText)) and parameters[1].valueAsText:
                PopulationCountField_Type = arcpy.ListFields(str(parameters[0].valueAsText),str(parameters[1].valueAsText))[0].type
                if PopulationCountField_Type not in ["Double", "Integer", "SmallInteger", "BigInteger", "Single"]:
                        parameters[1].setErrorMessage("Population Count Field must be in Integer, Float or Double format.")

    def execute(self, parameters, messages):
        """Performing a set of actions in GIS after clicking the RUN button"""
        arcpy.env.overwriteOutput = True
        # Load variables
        InputFeatureLayer = parameters[0].valueAsText
        PopulationCountField = parameters[1].valueAsText
        TargetAreaPolygon = parameters[2].valueAsText
        CustomGridEnable = parameters[3].value
        CustomGridLayer = parameters[4].valueAsText
        Grid_Size = parameters[5].valueAsText
        Grid_Size_value_raw,Grid_Size_unit=Grid_Size.split(" ")
        Grid_Size_NoSQ_m = math.sqrt(float(Grid_Size_value_raw.replace(',', '.')) * arcpy.ArealUnitConversionFactor(from_unit=Grid_Size_unit, to_unit="SquareMeters"))
        Grid_ShapeType = parameters[6].valueAsText
        Grid_SpatialReference = parameters[5].valueAsText # Reference for all layers used!
        Workspace = parameters[8].valueAsText
        OutputType = parameters[9].valueAsText
        OutputName = parameters[10].valueAsText
        arcpy.AddMessage("The configuration loading was successful.")

        # Set a workspace
        arcpy.env.workspace = parameters[8].valueAsText
        arcpy.AddMessage("The workspace \"" + Workspace + "\" has been set up.")

        # Remove existing filenames
        if arcpy.Exists(OutputName):
                arcpy.management.Delete(OutputName)

        # Generate a grid by user-defined criteria or use custom grid
        TargetAreaPolygon_Describe = arcpy.Describe(TargetAreaPolygon) # For extent coordinates
        if (CustomGridEnable == True):
            if CustomGridLayer:
                grid_default = CustomGridLayer
                arcpy.AddMessage("Custom grid successfully loaded.")
            else:
                arcpy.AddError("Invalid or missing Custom Grid layer.")
                raise arcpy.ExecuteError()
        else:
            grid_default = arcpy.management.GenerateTessellation(Workspace + "\Grid", Extent=TargetAreaPolygon_Describe.extent,
                                          Size=Grid_Size, Shape_Type=Grid_ShapeType.upper().replace(" ", "_"),
                                          H3_Resolution=7, Spatial_Reference=Grid_SpatialReference)
            arcpy.AddMessage("Grid (Size = " + Grid_Size + ", Shape Type = " + Grid_ShapeType + ") successfully generated.")

        # Select grid cells which have intersect with Target Area Polygon only and save
        grid_default_select = arcpy.management.SelectLayerByLocation(grid_default, overlap_type="INTERSECT", select_features=TargetAreaPolygon, selection_type="NEW_SELECTION")
        grid_adjusted = arcpy.CopyFeatures_management(grid_default_select, Workspace + "\Grid_TargetArea")
        arcpy.AddMessage("Grid adjusted to Target Area.")

        # Input Layer Clip to Target Area
        clip_InputFeatureLayer = arcpy.analysis.Clip(InputFeatureLayer, TargetAreaPolygon, "Clip_InputFeatureLayer")

        # Aggregation
        aggregation = arcpy.analysis.SummarizeWithin(grid_adjusted, clip_InputFeatureLayer, "SummarizeWithin_InputFeatureLayer",
                               "KEEP_ALL", [[PopulationCountField, 'SUM']],
                               "NO_SHAPE_SUM")
        aggregation_NF = arcpy.management.CalculateField(aggregation, "Population", '!sum_' + PopulationCountField + '!', "PYTHON3", field_type="DOUBLE")
        aggregation_NF_RF = arcpy.management.DeleteField(aggregation_NF, [['sum_' + PopulationCountField + '']], "DELETE_FIELDS")
        arcpy.AddMessage("Aggregation completed.")
        if OutputType == "Vector":
                arcpy.management.Rename(aggregation_NF_RF, OutputName, "FeatureClass")
                arcpy.AddMessage("The vector output \"" + OutputName + "\" is available in the output Geodatabase.")

        # Conversion to raster
        if OutputType == "Raster":
                raster = arcpy.conversion.FeatureToRaster(aggregation_NF_RF, "Population", OutputName, Grid_Size_NoSQ_m)
                arcpy.AddMessage("The raster output \"" + OutputName + "\" is available in the output Geodatabase.")

        # Delete temporary layers
        if (CustomGridEnable != True):
            arcpy.management.Delete(grid_default) # Prevent custom grid support layer from being deleted (custom grid is not a support layer!)
        arcpy.management.Delete(grid_adjusted)
        arcpy.management.Delete(clip_InputFeatureLayer)
        if OutputType == "Raster":
                arcpy.management.Delete(aggregation_NF_RF)

        # Add output to display (map)
        fc_path = f"{Workspace}\\{OutputName}"
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map_project = aprx.listMaps()[0]
        current_map_project.addDataFromPath(fc_path)
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return

class DailyState:
    def __init__(self):
        self.label = "Daily State of Population"
        self.description = "A tool for generating of the Daily State variant of the population grid in raster or vector form based on user-defined criteria."

    def getParameterInfo(self):
        """ PARAMETERS DEFINITION """

        """ Enable Economically inactive and Unemployed Population Layer """
        param_EcoInactivePopulation_Enable = arcpy.Parameter(displayName="Enable Economically inactive and Uemployed Population Layer",
                            name="enable_eco_inactive_population_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")
        param_EcoInactivePopulation_Enable.value = "True"        


        """ Economically inactive and Unemployed Population Layer """
        param_EcoInactivePopulationFeatureLayer = arcpy.Parameter(displayName="Economically inactive and Uemployed Population (Point Layer)",
                            name="eco_inactive_population_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for point data
        param_EcoInactivePopulationFeatureLayer.filter.list = ["Point"]


        """ Economically inactive and Unemployed Population Count Field """
        param_EcoInactivePopulationCountField = arcpy.Parameter(displayName="Number of Economically inactive and Uemployed Population (Field)",
                            name="eco_inactive_population_field",
                            datatype="Field",
                            parameterType="Optional",
                            direction="Input")
        # Show a list of EcoInactivePopulationFeatureLayer's attributes
        param_EcoInactivePopulationCountField.parameterDependencies = [param_EcoInactivePopulationFeatureLayer.name]

        """ Enable Working Population and Employees Layer """
        param_WorkingPopulationEmployees_Enable = arcpy.Parameter(displayName="Enable Working Population and Employees Layer",
                            name="enable_working_population_employees_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")
        param_WorkingPopulationEmployees_Enable.value = "False"
        

        """ Point Working Population and Employees Layer """
        param_WorkingPopulationEmployeesLayer = arcpy.Parameter(displayName="Working Population and Employees (Point Layer)",
                            name="working_population_employees_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for point data
        param_WorkingPopulationEmployeesLayer.filter.list = ["Point"]


        """ Number of Working Population and Employees Field """
        param_WorkingPopulationEmployeesField = arcpy.Parameter(displayName="Number of Working Population and Employees (Field)",
                            name="working_population_employees_field",
                            datatype="Field",
                            parameterType="Optional",
                            direction="Input")
        # Show a list of WorkingPopulationLayer's attributes
        param_WorkingPopulationEmployeesField.parameterDependencies = [param_WorkingPopulationEmployeesLayer.name]

        """ Enable Children and Students Layer """
        param_ChildrenStudents_Enable = arcpy.Parameter(displayName="Enable Children and Students Layer",
                            name="enable_children_students_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")
        param_ChildrenStudents_Enable.value = "False"                         


        """ Children and Students Point Layer """
        param_ChildrenStudentsLayer = arcpy.Parameter(displayName="Children and Students (Point Layer)",
                            name="children_students_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for point data
        param_ChildrenStudentsLayer.filter.list = ["Point"]


        """ Number of Children and Students Field """
        param_ChildrenStudentsField = arcpy.Parameter(displayName="Number of Children and Students in Educational Institutions (Field)",
                            name="children_students_field",
                            datatype="Field",
                            parameterType="Optional",
                            direction="Input")
        # Show a list of ChildrenStudentsLayer's attributes
        param_ChildrenStudentsField.parameterDependencies = [param_ChildrenStudentsLayer.name]

        """ Enable Teachers and School Facilities Staff Layer """
        param_TeachersSchoolFacilitiesStaff_Enable = arcpy.Parameter(displayName="Enable Teachers and Educational Institutions Staff Layer",
                            name="enable_teachers_school_facilities_staff_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")            
        param_TeachersSchoolFacilitiesStaff_Enable.value = "False"
        

        """ Teachers and School Facilities Staff Layer """
        param_TeachersSchoolFacilitiesStaffLayer = arcpy.Parameter(displayName="Teachers and Educational Institutions Staff (Point Layer)",
                            name="teachers_school_facilities_staff_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for point data
        param_TeachersSchoolFacilitiesStaffLayer.filter.list = ["Point"]


        """ Number of Teachers and School Facilities Staff Field """
        param_TeachersSchoolFacilitiesStaffField = arcpy.Parameter(displayName="Number of Teachers and Educational Institutions Staff (Field)",
                            name="teachers_school_facilities_staff_field",
                            datatype="Field",
                            parameterType="Optional",
                            direction="Input")
        # Show a list of TeachersSchoolFacilitiesStuffLayer's attributes
        param_TeachersSchoolFacilitiesStaffField.parameterDependencies = [param_TeachersSchoolFacilitiesStaffLayer.name]


        """ Enable Retirees Layer """
        param_Retirees_Enable = arcpy.Parameter(displayName="Enable Eldery Population Layer",
                            name="enable_retirees_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")
        param_Retirees_Enable.value = "False"


        """ Retirees Layer """
        param_RetireesLayer = arcpy.Parameter(displayName="Eldery Population (Point Layer)",
                            name="retirees_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for point data
        param_RetireesLayer.filter.list = ["Point"]


        """ Number of Retirees Field """
        param_RetireesField = arcpy.Parameter(displayName="Number of Pensioners/Retirees (Field)",
                            name="retirees_field",
                            datatype="Field",
                            parameterType="Optional",
                            direction="Input")
        # Show a list of RetireesLayer's attributes
        param_RetireesField.parameterDependencies = [param_RetireesLayer.name]


        """ Target Area Polygon """
        param_TargetAreaPolygon = arcpy.Parameter(displayName="Target Area (Polygon Layer)",
                            name="target_area_polygon",
                            datatype="GPFeatureLayer",
                            parameterType="Required",
                            direction="Input")
        # Only for polygon data
        param_TargetAreaPolygon.filter.list = ["Polygon"]

        """ Enable Custom Grid Option """
        param_CustomGrid_Enable = arcpy.Parameter(displayName="Enable Custom Grid Layer",
                            name="enable_custom_grid_layer",
                            datatype="GPBoolean",
                            parameterType="Optional",
                            direction="Input")        


        """ Custom Grid Layer """
        param_CustomGridLayer = arcpy.Parameter(displayName="Custom Grid Layer (Polygon Layer)",
                            name="custom_grid_layer",
                            datatype="GPFeatureLayer",
                            parameterType="Optional",
                            direction="Input")
        # Only for polygon data
        param_CustomGridLayer.filter.list = ["Polygon"]


        """ Grid Cell Size """
        param_GridCellSize = arcpy.Parameter(displayName="Grid Cell Size",
                            name="grid_cell_size",
                            datatype="GPArealUnit",
                            parameterType="Required",
                            direction="Input")
        # Default value (1 SqKm)
        param_GridCellSize.value = "1 SquareKilometers"


        """ Grid Shape Type """
        param_GridShapeType = arcpy.Parameter(displayName="Grid Cell Shape",
                            name="grid_shape_type",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Set a value list of grid shape types
        param_GridShapeType.filter.type = "ValueList"
        param_GridShapeType.filter.list = ["Square", "Triangle", "Hexagon", "Transverse Hexagon", "Diamond"]
        # Default value (0=Square)
        param_GridShapeType.value = param_GridShapeType.filter.list[0]


        """ Spatial Reference """
        param_SpatialReference = arcpy.Parameter(displayName="Spatial Reference",
                            name="spatial_reference",
                            datatype="GPSpatialReference",
                            parameterType="Required",
                            direction="Input")
        # Default value (5514=S-JTSK_Krovak_East_North)
        param_SpatialReference.values = arcpy.SpatialReference(5514)


        """ Output Geodatabase """
        param_Workspace = arcpy.Parameter(displayName="Output Geodatabase",
                            name="output_workspace",
                            datatype="DEWorkspace",
                            parameterType="Required",
                            direction="Input")
        # Allow to select Geodatabase path only
        param_Workspace.filter.list = ["Local Database"]


        """ Output Type """
        param_OutputType = arcpy.Parameter(displayName="Output Type",
                            name="output_type",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Set a value list of grid shape types
        param_OutputType.filter.type = "ValueList"
        param_OutputType.filter.list = ["Raster", "Vector"]
        # Default value (0=Raster)
        param_OutputType.values = param_OutputType.filter.list[0]


        """ Output Feature Class Name """
        param_OutputName = arcpy.Parameter(displayName="Output Name",
                            name="output_name",
                            datatype="GPString",
                            parameterType="Required",
                            direction="Input")
        # Default output filename
        param_OutputName.value = "PopulationGrid_DailyState"

        """ Active parameters array """
        params = [param_EcoInactivePopulation_Enable, param_EcoInactivePopulationFeatureLayer, param_EcoInactivePopulationCountField,
                  param_WorkingPopulationEmployees_Enable, param_WorkingPopulationEmployeesLayer, param_WorkingPopulationEmployeesField,
                  param_ChildrenStudents_Enable, param_ChildrenStudentsLayer, param_ChildrenStudentsField,
                  param_TeachersSchoolFacilitiesStaff_Enable, param_TeachersSchoolFacilitiesStaffLayer, param_TeachersSchoolFacilitiesStaffField,
                  param_Retirees_Enable, param_RetireesLayer, param_RetireesField,
                  param_TargetAreaPolygon, param_CustomGrid_Enable, param_CustomGridLayer,
                  param_GridCellSize, param_GridShapeType, param_SpatialReference,
                  param_Workspace, param_OutputType, param_OutputName]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Enabling the input layers"""
        # If the calling field is checked, I activate the target field and the field right after it
        def enable_fields(call_field_index, first_target_field_index, c):
            if parameters[call_field_index].value:
                parameters[first_target_field_index].enabled = True
                if c == 2:
                    parameters[first_target_field_index+1].enabled = True
            else:
                parameters[first_target_field_index].enabled = False
                if c == 2:
                    parameters[first_target_field_index+1].enabled = False

        enable_fields(16, 17, 1)
        enable_fields(0, 1, 2)
        enable_fields(3, 4, 2)
        enable_fields(6, 7, 2)
        enable_fields(9, 10, 2)
        enable_fields(12, 13, 2)
        
        # If the custom grid option checked, deactivate parameter fields for generating a new grid
        if parameters[16].value:
            parameters[18].enabled = False
            parameters[19].enabled = False
        else:
            parameters[18].enabled = True
            parameters[19].enabled = True


        """Modifying the values and properties of parameters before internal validation (when the parameter is changed)"""
        # Re-change Number of Economically inactive and Unemployed Population Field value if altered Economically inactive and Unemployed Population Layer
        def fval_remove_onLayerChange(field_param_index, layer_param_index):
                if parameters[layer_param_index].altered and not parameters[layer_param_index].hasBeenValidated:
                        parameters[field_param_index].value = ""

        # Remove field value if Input Feature Layer changed
        fval_remove_onLayerChange(2, 1)
        fval_remove_onLayerChange(5, 4)
        fval_remove_onLayerChange(8, 7)
        fval_remove_onLayerChange(11, 10)
        fval_remove_onLayerChange(14, 13)


        return

    def updateMessages(self, parameters):
        """Additional field check (invoked after changing the value in the corresponding field)"""
        Grid_Size = parameters[18].valueAsText
        if  Grid_Size is not None:   
                Grid_Size_value_raw,Grid_Size_unit=Grid_Size.split(" ")
                # Error message at zero/negative grid size value (Grid Cell Size parameter)
                if float(Grid_Size_value_raw.replace(',', '.')) <= 0:
                        parameters[18].setErrorMessage("Grid Cell size cannot be zero or negative!")

                # Disabling the use of Unknown unit in Grid Cell Size Areal Unit Field
                if str(Grid_Size_unit) == "Unknown":
                        parameters[18].setErrorMessage("The use of the \"Unknown\" unit is not allowed within this toolbox. Choose a different spatial unit.")

        # Function to check Input Feature Layer projection mismatch with defined Spatial Reference
        def layer_projection_mismatch(layer_param_index, layer_name, spref_field_index):
                if str(parameters[layer_param_index].valueAsText) != "" and arcpy.Exists(str(parameters[layer_param_index].valueAsText)):
                        SR_InputFeatureLayer = arcpy.Describe(str(parameters[layer_param_index].valueAsText)).spatialReference.name
                        SR_Field = arcpy.SpatialReference()
                        SR_Field.loadFromString(parameters[spref_field_index].valueAsText)
                        if SR_InputFeatureLayer != SR_Field.name:
                                parameters[layer_param_index].setErrorMessage(str(layer_name) + "'s projection mismatch with defined Spatial Reference.")
        # Input Layers projection mismatch checks
        layer_projection_mismatch(1, "Economically inactive and Unemployed Population Layer", 20)
        layer_projection_mismatch(4, "Working Population and Employees Layer", 20)
        layer_projection_mismatch(7, "Children and Students Layer", 20)
        layer_projection_mismatch(10, "Teachers and Educational Institutions Staff Layer", 20)
        layer_projection_mismatch(13, "Eldery Population Layer", 20)

        # Target Area Polygon projection mismatch with defined Spatial Reference
        if str(parameters[15].valueAsText) != "" and arcpy.Exists(str(parameters[15].valueAsText)):
                SR_InputFeatureLayer = arcpy.Describe(str(parameters[15].valueAsText)).spatialReference.name
                SR_Field = arcpy.SpatialReference()
                SR_Field.loadFromString(parameters[20].valueAsText)
                if SR_InputFeatureLayer != SR_Field.name:
                        parameters[15].setErrorMessage("Target Area Polygon's projection mismatch with defined Spatial Reference.")

        # Check Population Fields Function
        def check_field_type(field_param_index, field_name, layer_param_index):
                if arcpy.Exists(str(parameters[layer_param_index].valueAsText)) and parameters[field_param_index].valueAsText:
                        PopulationCountField_Type = arcpy.ListFields(str(parameters[layer_param_index].valueAsText),str(parameters[field_param_index].valueAsText))[0].type
                        if PopulationCountField_Type not in ["Double", "Integer", "SmallInteger", "BigInteger", "Single"]:
                                parameters[field_param_index].setErrorMessage(str(field_name) + " must be in Integer, Float or Double format.")
        # Check Population Fields types
        check_field_type(2, "Number of Economically inactive and Uemployed Population Field", 1)
        check_field_type(5, "Number of Working Population and Employees Field", 4)
        check_field_type(8, "Number of Children and Students in Educational Institutions Field", 7)
        check_field_type(11, "Number of Techers and Educational Institutions Staff Field", 10)
        check_field_type(14, "Number of Pensioners/Retirees Field", 13)

        # Check if at least one input layer (partial population state) is enabled
        if (parameters[0].value == False and parameters[3].value == False and parameters[6].value == False and parameters[9].value == False and parameters[12].value == False):
                err = "At least one input layer must be enabled"
                parameters[0].setErrorMessage(err)
                parameters[3].setErrorMessage(err)
                parameters[6].setErrorMessage(err)
                parameters[9].setErrorMessage(err)
                parameters[12].setErrorMessage(err)



    def execute(self, parameters, messages):
        """Performing a set of actions in GIS after clicking the RUN button"""
        arcpy.env.overwriteOutput = True

        # Load variables
        EcoInactiveUnemployedEnable = parameters[0].value
        EcoInactiveUnemployedLayer = parameters[1].valueAsText
        EcoInactiveUnemployedField = parameters[2].valueAsText
        WorkingEmployeesEnable = parameters[3].value
        WorkingEmployeesLayer = parameters[4].valueAsText
        WorkingEmployeesField = parameters[5].valueAsText
        ChildrenStudentsEnable = parameters[6].value
        ChildrenStudentsLayer = parameters[7].valueAsText
        ChildrenStudentsField = parameters[8].valueAsText
        TeachersSchoolStaffEnable = parameters[9].value
        TeachersSchoolStaffLayer = parameters[10].valueAsText
        TeachersSchoolStaffField = parameters[11].valueAsText
        RetireesEnable = parameters[12].value
        RetireesLayer = parameters[13].valueAsText
        RetireesField = parameters[14].valueAsText
        TargetAreaPolygon = parameters[15].valueAsText
        CustomGridEnable = parameters[16].value
        CustomGridLayer = parameters[17].valueAsText
        Grid_Size = parameters[18].valueAsText
        Grid_Size_value_raw,Grid_Size_unit=Grid_Size.split(" ")
        Grid_Size_NoSQ_m = math.sqrt(float(Grid_Size_value_raw.replace(',', '.')) * arcpy.ArealUnitConversionFactor(from_unit=Grid_Size_unit, to_unit="SquareMeters"))
        Grid_ShapeType = parameters[19].valueAsText
        Grid_SpatialReference = parameters[20].valueAsText # Reference for all layers used!
        Workspace = parameters[21].valueAsText
        OutputType = parameters[22].valueAsText
        OutputName = parameters[23].valueAsText
        arcpy.AddMessage("The configuration loading was successful.")

        # Set a workspace
        arcpy.env.workspace = parameters[21].valueAsText
        arcpy.AddMessage("The workspace \"" + Workspace + "\" has been set up.")

        # Remove existing filenames
        if arcpy.Exists(OutputName):
                arcpy.management.Delete(OutputName)

        # Generate a grid by user-defined criteria or use custom
        TargetAreaPolygon_Describe = arcpy.Describe(TargetAreaPolygon) # For extent coordinates
        if (CustomGridEnable == True):
            if (CustomGridLayer):
                grid_default = CustomGridLayer
                arcpy.AddMessage("Custom grid successfully loaded.")
            else:
                arcpy.AddError("Invalid or missing Custom Grid layer.")
                raise arcpy.ExecuteError()
        else:  
            grid_default = arcpy.management.GenerateTessellation(Workspace + "\Grid", Extent=TargetAreaPolygon_Describe.extent,
                                          Size=Grid_Size, Shape_Type=Grid_ShapeType.upper().replace(" ", "_"),
                                          H3_Resolution=7, Spatial_Reference=Grid_SpatialReference)
            arcpy.AddMessage("Grid (Size = " + Grid_Size + ", Shape Type = " + Grid_ShapeType + ") successfully generated.")

        # Select grid cells which have intersect with Target Area Polygon only and save
        grid_default_select = arcpy.management.SelectLayerByLocation(grid_default, overlap_type="INTERSECT", select_features=TargetAreaPolygon, selection_type="NEW_SELECTION")
        grid_adjusted = arcpy.CopyFeatures_management(grid_default_select, Workspace + "\Grid_TargetArea")
        arcpy.AddMessage("Grid adjusted to Target Area.")

        # Input Layers Clip to Target Area
        if EcoInactiveUnemployedEnable == True:
                clip_EcoInactiveUnemployedLayer = arcpy.analysis.Clip(EcoInactiveUnemployedLayer, TargetAreaPolygon, "Clip_EcoInactiveUnemployedLayer")
        if WorkingEmployeesEnable == True:
                clip_WorkingEmployeesLayer = arcpy.analysis.Clip(WorkingEmployeesLayer, TargetAreaPolygon, "Clip_WorkingEmployeesLayer")
        if ChildrenStudentsEnable == True:
                clip_ChildrenStudentsLayer = arcpy.analysis.Clip(ChildrenStudentsLayer, TargetAreaPolygon, "Clip_ChildrenStudentsLayer")    
        if TeachersSchoolStaffEnable == True:
                clip_TeachersSchoolStaffLayer = arcpy.analysis.Clip(TeachersSchoolStaffLayer, TargetAreaPolygon, "Clip_TeachersSchoolStaffLayer")
        if RetireesEnable == True:
                clip_RetireesLayer = arcpy.analysis.Clip(RetireesLayer, TargetAreaPolygon, "Clip_RetireesLayer")
        arcpy.AddMessage("Clip of All Input Layers completed.")

        # Field Transformations
        if EcoInactiveUnemployedEnable == True:
                FT_EcoInactiveUnemployedLayer = arcpy.management.CalculateField(clip_EcoInactiveUnemployedLayer, "PopField1", '!' + EcoInactiveUnemployedField + '!', "PYTHON3", field_type="DOUBLE")
        if WorkingEmployeesEnable == True:
                FT_WorkingEmployeesLayer = arcpy.management.CalculateField(clip_WorkingEmployeesLayer, "PopField2", '!' + WorkingEmployeesField + '!', "PYTHON3", field_type="DOUBLE")
        if ChildrenStudentsEnable == True:
                FT_ChildrenStudentsLayer = arcpy.management.CalculateField(clip_ChildrenStudentsLayer, "PopField3", '!' + ChildrenStudentsField + '!', "PYTHON3", field_type="DOUBLE")
        if TeachersSchoolStaffEnable == True:
                FT_TeachersSchoolStaffLayer = arcpy.management.CalculateField(clip_TeachersSchoolStaffLayer, "PopField4", '!' + TeachersSchoolStaffField + '!', "PYTHON3", field_type="DOUBLE")
        if RetireesEnable == True:
                FT_RetireesLayer = arcpy.management.CalculateField(clip_RetireesLayer, "PopField5", '!' + RetireesField + '!', "PYTHON3", field_type="DOUBLE")
        arcpy.AddMessage("Field Transformations completed.")

        # Parital Aggregations
        aggregation_EcoInactiveUnemployedLayer = aggregation_WorkingEmployeesLayer = aggregation_ChildrenStudentsLayer = aggregation_TeachersSchoolStaffLayer = aggregation_RetireesLayer = []
        sum_expression = str()
        if EcoInactiveUnemployedEnable == True:
                aggregation_EcoInactiveUnemployedLayer = arcpy.analysis.SummarizeWithin(grid_adjusted, FT_EcoInactiveUnemployedLayer, "SummarizeWithin_EcoInactiveUnemployedLayer",
                                       "KEEP_ALL", [['PopField1', 'SUM']],
                                       "NO_SHAPE_SUM")
                arcpy.AddMessage("Partial Aggregation #1 completed.")
                sum_expression += "!sum_PopField1!+"
        if WorkingEmployeesEnable == True:
                aggregation_WorkingEmployeesLayer = arcpy.analysis.SummarizeWithin(grid_adjusted, FT_WorkingEmployeesLayer, "SummarizeWithin_WorkingEmployeesLayer",
                                       "KEEP_ALL", [['PopField2', 'SUM']],
                                       "NO_SHAPE_SUM")
                arcpy.AddMessage("Partial Aggregation #2 completed.")
                sum_expression += "!sum_PopField2!+"
        if ChildrenStudentsEnable == True:
                aggregation_ChildrenStudentsLayer = arcpy.analysis.SummarizeWithin(grid_adjusted, FT_ChildrenStudentsLayer, "SummarizeWithin_ChildrenStudentsLayer",
                                       "KEEP_ALL", [['PopField3', 'SUM']],
                                       "NO_SHAPE_SUM")
                arcpy.AddMessage("Partial Aggregation #3 completed.")
                sum_expression += "!sum_PopField3!+"
        if TeachersSchoolStaffEnable == True:
                aggregation_TeachersSchoolStaffLayer = arcpy.analysis.SummarizeWithin(grid_adjusted, FT_TeachersSchoolStaffLayer, "SummarizeWithin_TeachersSchoolStaffLayer",
                                       "KEEP_ALL", [['PopField4', 'SUM']],
                                       "NO_SHAPE_SUM")
                arcpy.AddMessage("Partial Aggregation #4 completed.")
                sum_expression += "!sum_PopField4!+"
        if RetireesEnable == True:
                aggregation_RetireesLayer = arcpy.analysis.SummarizeWithin(grid_adjusted, FT_RetireesLayer, "SummarizeWithin_RetireesLayer",
                                       "KEEP_ALL", [['PopField5', 'SUM']],
                                       "NO_SHAPE_SUM")
                arcpy.AddMessage("Partial Aggregation #5 completed.")
                sum_expression += "!sum_PopField4!+"

        # Union of Partial Aggregations (Merge aggregated attributes to one layer)
        union = arcpy.analysis.Union([aggregation_EcoInactiveUnemployedLayer, aggregation_WorkingEmployeesLayer, aggregation_ChildrenStudentsLayer,
                                      aggregation_TeachersSchoolStaffLayer, aggregation_RetireesLayer],
                                      "Partial_Aggregations_Union", "ALL")
        arcpy.AddMessage("Union of Partial Aggregations completed.")
        
        # Removing the last occurrence function (to remove the last plus "+" sign in the compiled sum expression)
        def remove_last_occurrence_plus(s):
            index = s.rfind("+")
            if index != -1:
                return s[:index] + s[index+1:]
            return s

        # Final Aggregation
        final_sum_aggregation = arcpy.management.CalculateField(union, "Population",
                                      remove_last_occurrence_plus(sum_expression),
                                      "PYTHON3", field_type="DOUBLE")
        final_sum_aggregation_RF = arcpy.management.DeleteField(final_sum_aggregation, [['Population']], "KEEP_FIELDS")
        arcpy.AddMessage("Final Aggregation completed.")

        if OutputType == "Vector":
                arcpy.management.Rename(final_sum_aggregation_RF, OutputName, "FeatureClass")
                arcpy.AddMessage("The vector output \"" + OutputName + "\" is available in the output Geodatabase.")

        # Conversion to raster
        if OutputType == "Raster":
                raster = arcpy.conversion.FeatureToRaster(final_sum_aggregation_RF, "Population", OutputName, Grid_Size_NoSQ_m)
                arcpy.AddMessage("The raster output \"" + OutputName + "\" is available in the output Geodatabase.")

        # Delete temporary layers
        if (CustomGridEnable != True):
            arcpy.management.Delete(grid_default) # Prevent custom grid support layer from being deleted (custom grid is not a support layer!)
        arcpy.management.Delete(grid_adjusted)
        if EcoInactiveUnemployedEnable == True:
                arcpy.management.Delete(clip_EcoInactiveUnemployedLayer)
                arcpy.management.Delete(aggregation_EcoInactiveUnemployedLayer)
        if WorkingEmployeesEnable == True:
                arcpy.management.Delete(clip_WorkingEmployeesLayer)
                arcpy.management.Delete(aggregation_WorkingEmployeesLayer)
        if ChildrenStudentsEnable == True:
                arcpy.management.Delete(clip_ChildrenStudentsLayer)
                arcpy.management.Delete(aggregation_ChildrenStudentsLayer)
        if TeachersSchoolStaffEnable == True:
                arcpy.management.Delete(clip_TeachersSchoolStaffLayer)
                arcpy.management.Delete(aggregation_TeachersSchoolStaffLayer)
        if RetireesEnable == True:
                arcpy.management.Delete(clip_RetireesLayer)  
                arcpy.management.Delete(aggregation_RetireesLayer)
        arcpy.management.Delete(union)
        if OutputType == "Raster":
                arcpy.management.Delete(final_sum_aggregation_RF)

        # Add output to display (map)
        fc_path = f"{Workspace}\\{OutputName}"
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        current_map_project = aprx.listMaps()[0]
        current_map_project.addDataFromPath(fc_path)
        
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
