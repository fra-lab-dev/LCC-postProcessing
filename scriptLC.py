# -*- coding: utf-8  -*-

import os
import arcpy
#import difflib
import argparse
import ipdb


class createLCC():

    def __init__(self, gdb, dataset, rasAI, outPath, baseName):

        self.gdb = arcpy.Describe(gdb)
        self.dataset = arcpy.Describe(os.path.join( gdb, dataset ))
        self.rasAI = arcpy.Raster(rasAI)
        # ref_name, ref_ext = os.path.splitext(os.path.basename(self.rasAI.catalogPath))
        self.baseName = f"LC_{baseName}"

        if not os.path.exists(outPath):
            os.makedirs(outPath)
        self.outPath = outPath

        self.N_A = 999

        arcpy.env.overwriteOutput = True
        arcpy.env.workspace = gdb

        # outputCoordinateSystem = arcpy.SpatialReference(3035)
        #
        # transformation_list = arcpy.ListTransformations(self.rasAI.spatialReference, outputCoordinateSystem)
        # transformation_name = transformation_list[0] if len(transformation_list) > 0 else ''
        #
        # arcpy.env.outputCoordinateSystem = outputCoordinateSystem
        # arcpy.env.geographicTransformations = transformation_name
        arcpy.env.extent = self.rasAI.extent
        # arcpy.env.mask = self.rasAI.catalogPath
        arcpy.env.cellSize = self.rasAI.catalogPath
        arcpy.env.snapRaster = self.rasAI.catalogPath

        self.ait = os.path.join(gdb, dataset, 'ait')
        self.ait_l = os.path.join(gdb, dataset, 'ait_l')
        self.region = os.path.join(gdb, dataset, 'region')

        self.ancillary = os.path.join(gdb, 'ancillary')
        self.RulesOrdineCaricamento = os.path.join(gdb, 'RulesOrdineCaricamento')
        self.RulesXmatch = os.path.join(gdb, 'RulesXmatch')


        return

    def run(self):

        print (f"run() {self.rasAI.catalogPath}")
        arcpy.CheckOutExtension("Spatial")

        self.delete_tmp = True
        base_elab = True
        final_cleaning = True

        rasMask = arcpy.sa.Con(arcpy.sa.IsNull(self.rasAI) == 0, self.N_A)
        rasMask.save(f"{self.baseName}_rasMask")

        ### base elab

        lccRoads = self.lccRoads(rasMask) if base_elab else arcpy.Raster(f"{self.baseName}_lccRoads_rasMask") # strade 111

        lcc3 = self.lcc3(lccRoads)  if base_elab else arcpy.Raster(f"{self.baseName}_lcc3_rasMask") # acque
        lcc111 = self.lcc111(lcc3) if base_elab else arcpy.Raster(f"{self.baseName}_lcc111_rasMask") # Sealed Artificial Surfaces and Constructions
        lcc112 = self.lcc112(lcc111) if base_elab else arcpy.Raster(f"{self.baseName}_lcc112_rasMask") # Non-Sealed Artificial Surfaces

        lcc121 = self.lcc121(lcc112) if base_elab else arcpy.Raster(f"{self.baseName}_lcc121_rasMask") # Natural Consolidated Surfaces
        lcc122 = self.lcc122(lcc121) if base_elab else arcpy.Raster(f"{self.baseName}_lcc122_rasMask") # Natural Unconsolidated Surfaces

        # lccTrees = self.lccTrees(lcc122) if base_elab else arcpy.Raster(f"{self.baseName}_lccTrees_rasMask") # Trees Needle Leaved Evergreen Deciduous, Trees Broad Leaved Evergreen Deciduous
        lccTrees2111 = self.lccTrees2111(lcc122) if base_elab else arcpy.Raster(f"{self.baseName}_lccTrees2111_rasMask") # Trees Needle Leaved Evergreen Deciduous
        lccTrees2112 = self.lccTrees2112(lccTrees2111) if base_elab else arcpy.Raster(f"{self.baseName}_lccTrees2112_rasMask") # Trees Broad Leaved Evergreen Deciduous


        lcc212 = self.lcc212(lccTrees2112) if base_elab else arcpy.Raster(f"{self.baseName}_lcc212_rasMask") # Bushes
        lcc22 = self.lcc22(lcc212) if base_elab else arcpy.Raster(f"{self.baseName}_lcc22_rasMask")
        lcc32 = self.lcc32(lcc22) if base_elab else arcpy.Raster(f"{self.baseName}_lcc32_rasMask")

        ### Check Arboree

        lccCheckArb = self.lccCheckArb(lcc32) if base_elab else arcpy.Raster(f"{self.baseName}_lccCheckArb_rasMask")

        ### final cleaning

        if final_cleaning:
            shrink = self.shrink(lccCheckArb, 5, 999, 'MORPHOLOGICAL')
            # shrink.save(os.path.join(self.outPath, f"{self.baseName}_LCC.tif"))
            outRas = shrink
        else:
            outRas = lccCheckArb

        outRas = self.repairNoData(outRas)

        self.exportRas( outRas, self.outPath, f"{self.baseName}.tif")

        arcpy.CheckInExtension("Spatial")
        arcpy.ResetEnvironments()

        return

    def repairNoData(self, bRas):
        print(self.repairNoData.__name__)

        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.repairNoData.__name__}"

        nibbleOut = arcpy.sa.Int(arcpy.sa.Nibble(bRas, bRas, nibble_values="DATA_ONLY", nibble_nodata="PROCESS_NODATA"))

        nibbleOut.save(f"{tmpBaseName}_nibbleOut")

        arcpy.ClearEnvironment("mask")
        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return nibbleOut

    def lccCheckArb(self, bRas):

        print(self.lccCheckArb.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lccCheckArb.__name__}"

        mask46 = arcpy.analysis.Select(self.ait, 'ait_Select46', where_clause="RuleID IN (13)")
        mask47 = arcpy.analysis.Select(self.ait, 'ait_Select47', where_clause="RuleID IN (47)")

        select_ras46 = arcpy.conversion.PolygonToRaster(mask46, "RuleID", "select_ras46").getOutput(0)
        select_ras47 = arcpy.conversion.PolygonToRaster(mask47, "RuleID", "select_ras47").getOutput(0)

        IsNull46 = arcpy.sa.IsNull(arcpy.Raster(select_ras46))
        IsNull47 = arcpy.sa.IsNull(arcpy.Raster(select_ras47))


        # maskArb_21121 = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(select_ras46)) == 0, 21121) # evergreen
        # maskArb_21122 = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(select_ras47)) == 0, 21122) # deciduos

        # maskArb = arcpy.sa.Con(IsNull46 == 0, 21121, arcpy.sa.Con(IsNull47 == 0, 21122, 22) ) # deciduos
        maskArb = arcpy.sa.Con(IsNull47 == 0, 21122, 22 ) # deciduos

        maskRasSimply = self.symplyRaster(maskArb, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == 22, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        for i in [mask46, mask47, select_ras46, select_ras47]:
            arcpy.management.Delete(i)

        arcpy.ClearEnvironment("mask")

        return outCon

    def lcc3(self, bRas):
        print( self.lcc3.__name__)
        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lcc3.__name__}"

        outCon = arcpy.sa.Con(self.rasAI==3, 3112, self.N_A)

        maskRas = self.creaFcMask_lcc3(tmpBaseName, [1,4,5,3], [[5,3112],[4,3112],[3,3111],[1,312]], buffer="4 Meters")
        outCon = arcpy.sa.Con(maskRas != 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)
        outCon.save(f"{tmpBaseName}_rasMask_Simply")

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        arcpy.management.Delete(maskRas.catalogPath)
        arcpy.management.Delete(f"{tmpBaseName}_rasMask_Simply")
        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon
    def lcc111(self, bRas):
        print( self.lcc111.__name__)
        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lcc111.__name__}"

        outCon = arcpy.sa.Con(self.rasAI==111, 111, self.N_A)

        # maskRas = self.creaFcMask(tmpBaseName, [20, 21, 23, 31, 32, 33, 34, 41], all=111)
        # outCon = arcpy.sa.Con(maskRas != 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=1)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        # arcpy.management.Delete(maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon
    def lccRoads(self, bRas):
        print( self.lccRoads.__name__)
        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lccRoads.__name__}"

        riclassifica = [[20, 111], [21, 111], [23, 111], [31, 111], [32, 111], [33, 111], [34, 111], [41, 111],
                        [30, 112], [29, 112], [22, 112], [25, 112]]

        maskRas = self.creaFcMask(tmpBaseName, [20, 21, 23, 31, 32, 33, 34, 41, 30, 29, 22, 25], riclassifica=riclassifica)
        maskRasSimply = self.symplyRaster(maskRas, tmpBaseName, min_aggragate_cells=1)

        maskRasSimply = arcpy.sa.Con(maskRasSimply==1, self.N_A, maskRasSimply)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        arcpy.management.Delete(maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon
    def lcc112(self, bRas):
        print( self.lcc112.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lcc112.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 112, 112, self.N_A)
        # outCon.save("tmp")

        # maskRas = self.creaFcMask(tmpBaseName, [30,29,22,25], all=112)
        # outCon = arcpy.sa.Con(maskRas != 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=1)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        # arcpy.management.Delete (maskRasSimply.catalogPath)
        if self.delete_tmp: arcpy.management.Delete (bRas.catalogPath)

        arcpy.ClearEnvironment("mask")

        return outCon
    def lcc121(self, bRas):
        print( self.lcc121.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lcc121.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 121, 121, self.N_A)

        maskRas = self.creaFcMask(tmpBaseName, [27], riclassifica=[[27, 121]])
        outCon = arcpy.sa.Con(maskRas != 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.management.Delete (maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete (bRas.catalogPath)

        arcpy.ClearEnvironment("mask")

        return outCon
    def lcc122(self, bRas):
        print( self.lcc122.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lcc122.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 122, 122, self.N_A)

        maskRas = self.creaFcMask(tmpBaseName, [19,26], riclassifica=[[19, 122], [26, 122]])
        outCon = arcpy.sa.Con(maskRas != 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.management.Delete (maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete (bRas.catalogPath)

        arcpy.ClearEnvironment("mask")

        return outCon


    def lccTrees(self, bRas):
        print( self.lccTrees.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lccTrees.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 211, 1, self.N_A)

        rcls = [[6,21111],[7,21111],[37,21121],[9,21121],[13,21121],[38,21122],[10,21122],[14,21122]]
        maskRas = self.creaFcMaskInterpolate(tmpBaseName, [6,7, 37,9,13, 38,10,14], riclassifica=rcls)

        outCon = arcpy.sa.Con(outCon == 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.management.Delete (maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete (bRas.catalogPath)

        arcpy.ClearEnvironment("mask")
        
        return outCon


    def lccTrees2111(self, bRas):

        print(self.lccTrees2111.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lccTrees2111.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 2111, 21111, self.N_A)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        arcpy.ClearEnvironment("mask")

        return outCon

    def lccTrees2112(self, bRas):

        print(self.lccTrees2112.__name__)
        arcpy.env.mask = self.rasAI.catalogPath
        tmpBaseName = f"{self.baseName}_{self.lccTrees2112.__name__}"

        outCon = arcpy.sa.Con(self.rasAI == 2112, 1, self.N_A)

        rcls = [[37, 21121], [9, 21121], [13, 21121], [8, 21122], [10, 21122], [11, 21122], [14, 21122], [36, 21122], [38, 21122]]
        # rcls = [[37, 21121], [9, 21121], [8, 21122], [10, 21122], [11, 21122], [36, 21122], [38, 21122]]
        maskRas = self.creaFcMaskInterpolate(tmpBaseName, [37,9,13,8,10,11,14,36,38], riclassifica=rcls)

        outCon = arcpy.sa.Con(outCon == 1, maskRas, outCon)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.management.Delete(maskRas.catalogPath)
        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        arcpy.ClearEnvironment("mask")

        return outCon
    def lcc212(self, bRas):
        print( self.lcc212.__name__)

        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lcc212.__name__}"

        outCon = arcpy.sa.Con(self.rasAI==212, 212, self.N_A)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon

    def lcc22(self, bRas):
        print( self.lcc22.__name__)

        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lcc22.__name__}"

        InList = arcpy.sa.InList(self.rasAI,[223,224])

        outCon = arcpy.sa.Con(arcpy.sa.IsNull(InList)==0, 22, self.N_A)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon

    def lcc32(self, bRas):
        print( self.lcc32.__name__)

        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.lcc32.__name__}"

        outCon = arcpy.sa.Con(self.rasAI==32, 32, self.N_A)
        maskRasSimply = self.symplyRaster(outCon, tmpBaseName, min_aggragate_cells=2)

        outCon = arcpy.sa.Con(bRas == self.N_A, maskRasSimply, bRas)
        outCon.save(f"{tmpBaseName}_rasMask")

        arcpy.ClearEnvironment("mask")

        if self.delete_tmp: arcpy.management.Delete(bRas.catalogPath)

        return outCon

    def shrink(self, in_raster, number_cells, zone_values, shrink_method='DISTANCE'):

        print(f"shrink {in_raster.name} number_cells {number_cells}, zone_values {zone_values}, shrink_method {shrink_method}")

        arcpy.env.mask = self.rasAI.catalogPath

        tmpBaseName = f"{self.baseName}_{self.shrink.__name__}{zone_values}"

        shrink = arcpy.sa.Shrink(in_raster, number_cells, zone_values, shrink_method)
        shrink.save(f"{tmpBaseName}")

        arcpy.ClearEnvironment("mask")

        if self.delete_tmp: arcpy.management.Delete(in_raster.catalogPath)

        return shrink
    def creaFcMask_lcc3(self, tmpBaseName, rulesIds=[], riclassifica=[], buffer=None):

        print (f"\tcreaFcMask ( {tmpBaseName}, {rulesIds} )")

        transformation_list = arcpy.ListTransformations(self.dataset.spatialReference, self.rasAI.spatialReference, self.dataset.extent)
        geographicTransformations = transformation_list[0] if len(transformation_list) > 0 else ''
        arcpy.env.outputCoordinateSystem = self.rasAI.spatialReference
        arcpy.env.geographicTransformations = geographicTransformations

        maskShps = list()

        for rulesID in rulesIds:
            select = arcpy.analysis.Select(self.ait, f"{tmpBaseName}_fcMask_{rulesID}",  where_clause=f"RuleID IN ({rulesID})").getOutput(0)
            if rulesID == 3:
                bufferFc = arcpy.analysis.Buffer(select, f"{tmpBaseName}_fcMask_{rulesID}_Buffer", buffer ).getOutput(0)
                maskShps.append(bufferFc)
                arcpy.management.Delete(select)
            else:
                maskShps.append( select )

        maskShp = arcpy.management.Merge(maskShps, f"{tmpBaseName}_fcMask").getOutput(0)

        for fc in maskShps:
            arcpy.management.Delete(fc)

        maskShpToRas = arcpy.conversion.PolygonToRaster(maskShp, "RuleID", f"{tmpBaseName}_fcMaskToRas").getOutput(0)

        RemapValue = arcpy.sa.RemapValue(riclassifica )
        outReclass1 = arcpy.sa.Reclassify(maskShpToRas, "Value", RemapValue)

        fcRasNull = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(outReclass1))==0, outReclass1, 1)
        fcRasNull.save(f"{tmpBaseName}_fcMaskRasNull")

        arcpy.management.Delete(maskShpToRas)
        arcpy.management.Delete(maskShp)

        arcpy.ClearEnvironment("outputCoordinateSystem")
        arcpy.ClearEnvironment("geographicTransformations")

        return fcRasNull
    def creaFcMask(self, tmpBaseName, rulesIds=[], riclassifica=None, all=None):

        print (f"\tcreaFcMask ( {tmpBaseName}, {rulesIds} )")

        transformation_list = arcpy.ListTransformations(self.dataset.spatialReference, self.rasAI.spatialReference, self.dataset.extent)
        geographicTransformations = transformation_list[0] if len(transformation_list) > 0 else ''
        arcpy.env.outputCoordinateSystem = self.rasAI.spatialReference
        arcpy.env.geographicTransformations = geographicTransformations

        maskShp = arcpy.analysis.Select(self.ait, f"{tmpBaseName}_fcMask", where_clause=f"RuleID IN ({','.join([str(i) for i in rulesIds])})").getOutput(0)
        maskShpToRas = arcpy.conversion.PolygonToRaster(maskShp, "RuleID", f"{tmpBaseName}_fcMaskToRas").getOutput(0)

        if int(arcpy.management.GetCount(maskShp).getOutput(0)) == 0:
            maskShpToRasIsNUll = True
        else:
            maskShpToRasIsNUll = False

        check_any = False
        if any(x in [20,25,45] for x in rulesIds):
            maskShpL = arcpy.analysis.Select(self.ait_l, f"{tmpBaseName}_fcLMask", where_clause=f"RuleID IN ({','.join([str(i) for i in rulesIds])})").getOutput(0)
            if int(arcpy.management.GetCount(maskShpL).getOutput(0)) > 0:
                maskShpToRasL_out = arcpy.conversion.PolylineToRaster(maskShpL, "RuleID", f"{tmpBaseName}_fcLMaskToRas0").getOutput(0)
                maskShpToRasL = arcpy.sa.Con(arcpy.Raster(maskShpToRasL_out) > 0, maskShpToRasL_out)
                maskShpToRasL.save(f"{tmpBaseName}_fcLMaskToRas")
                check_any = True
                if riclassifica:
                    RemapValue = arcpy.sa.RemapValue(riclassifica)
                    outReclass1_Line = arcpy.sa.Reclassify(maskShpToRasL, "Value", RemapValue)
                if all:
                    outReclass1_Line = arcpy.sa.Con(maskShpToRasL, all)
            else:
                check_any = False
            arcpy.management.Delete(maskShpL)
            arcpy.management.Delete(maskShpToRasL_out)

        if riclassifica:
            if not maskShpToRasIsNUll:
                RemapValue = arcpy.sa.RemapValue(riclassifica )
                outReclass1 = arcpy.sa.Reclassify(maskShpToRas, "Value", RemapValue)
            else:
                outReclass1 = maskShpToRas
        if all:
            if not maskShpToRasIsNUll:
                outReclass1 = arcpy.sa.Con(maskShpToRas, all)
            else:
                outReclass1 = maskShpToRas

        if check_any:
            outReclass1 = arcpy.sa.Con(arcpy.sa.IsNull(maskShpToRas)==1, outReclass1_Line, outReclass1)
            # outReclass1.save(f"{tmpBaseName}_outReclass1")

        fcRasNull = arcpy.sa.Con(arcpy.sa.IsNull(arcpy.Raster(outReclass1))==0, outReclass1, 1)
        fcRasNull.save(f"{tmpBaseName}_fcMaskRasNull")

        try:
            arcpy.management.Delete(f"{tmpBaseName}_fcLMaskToRas")
        except:
            pass
        arcpy.management.Delete(maskShpToRas)
        arcpy.management.Delete(maskShp)

        arcpy.ClearEnvironment("outputCoordinateSystem")
        arcpy.ClearEnvironment("geographicTransformations")

        # if any([x in tmpBaseName for x in ['lcc111', 'lcc112']]):
        #     return fcRasNull

        return fcRasNull
    def creaFcMaskInterpolate(self, tmpBaseName, rulesIds=[], riclassifica=None):

        print (f"\tcreaFcMaskInterpolate ( {tmpBaseName}, {rulesIds} )")

        transformation_list = arcpy.ListTransformations(self.dataset.spatialReference, self.rasAI.spatialReference, self.dataset.extent)
        geographicTransformations = transformation_list[0] if len(transformation_list) > 0 else ''
        arcpy.env.outputCoordinateSystem = self.rasAI.spatialReference
        arcpy.env.geographicTransformations = geographicTransformations

        maskShp = arcpy.analysis.Select(self.ait, f"{tmpBaseName}_fcMask", where_clause=f"RuleID IN ({','.join([str(i) for i in rulesIds])})").getOutput(0)

        maskShpToRas = arcpy.conversion.PolygonToRaster(maskShp, "RuleID", f"{tmpBaseName}_fcMaskToRas").getOutput(0)

        RemapValue = arcpy.sa.RemapValue(riclassifica )
        outReclass1 = arcpy.sa.Reclassify(maskShpToRas, "Value", RemapValue)
        nibbleOut = arcpy.sa.Nibble(outReclass1, outReclass1, nibble_values="DATA_ONLY", nibble_nodata="PROCESS_NODATA")
        nibbleOut.save(f"{tmpBaseName}_fcMaskRasNull")

        arcpy.management.Delete(maskShpToRas)
        arcpy.management.Delete(maskShp)

        arcpy.ClearEnvironment("outputCoordinateSystem")
        arcpy.ClearEnvironment("geographicTransformations")

        return nibbleOut

    def exportRas(self, inRas, outFolder, outName):


        print (f"export( {outName} )")

        outputCoordinateSystem = arcpy.SpatialReference(3035)

        transformation_list = arcpy.ListTransformations(inRas.spatialReference, outputCoordinateSystem, inRas.extent)
        transformation_name = transformation_list[0] if len(transformation_list) > 0 else ''

        arcpy.env.outputCoordinateSystem = outputCoordinateSystem
        arcpy.env.geographicTransformations = transformation_name
        arcpy.env.snapRaster = inRas.catalogPath

        if arcpy.Exists( os.path.join(outFolder, outName) ):
            arcpy.management.Delete( os.path.join(outFolder, outName) )

        # inRas.save(os.path.join(outFolder, outName))

        arcpy.management.ProjectRaster(inRas.catalogPath, os.path.join(outFolder, outName), outputCoordinateSystem,
                                      geographic_transform=transformation_name)

        if self.delete_tmp: arcpy.management.Delete(inRas.catalogPath)

        return
    def symplyRaster(self, in_raster, ref_name, min_aggragate_cells=2):

        print(f"\tsymplyRaster (mmu = {min_aggragate_cells} pixel)")

        RgnGrp = arcpy.sa.RegionGroup(in_raster, "FOUR", add_link="NO_LINK")
        RgnGrp.save(f"{ref_name}_simplyTmp")

        in_mask_raster = arcpy.sa.Con(RgnGrp, 1, where_clause=f"Count > {min_aggragate_cells}" )
        nibbleOut  = arcpy.sa.Nibble(in_raster, in_mask_raster, nibble_values="DATA_ONLY", nibble_nodata="PRESERVE_NODATA")

        arcpy.management.Delete(RgnGrp.catalogPath)

        return nibbleOut






if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Script post-processing Land Cover Mapping")

    parser.add_argument("--pathInf", type=str, help="Path to Inference map")
    parser.add_argument("--pathOut", type=str, help="Path to Output map")
    parser.add_argument("--output", type=str, help="Name of Output map")
    parser.add_argument("--tile", type=str, help="Tile to process")

    args = parser.parse_args()


    # TODO da prendere in configurazione
    gdb = r"C:\Users\FrancescoGeri\Downloads\DBNS_test\DBNS_test.gdb"
    dataset = 'ITALIA'
    tiles = os.path.join(gdb, "Tiles")
    versione = 3

    # rasRef = os.path.join(r"\\cfsnas\VALIDATION2018\pnnr\SE_S4_01\inference", r"T33TTG_2022_inference_ispra_v2_filtro1px.tif")
    #r"\\cfsnas\VALIDATION2018\pnnr\SE_S4_01\WORK\Inference\Sample_ObjectBased"
    #inferencePath = r"C:\\Users\\FrancescoGeri\\Documents\\Lavori\\eGeos\\satellite2forest\\dataset"
    #outBasePath = r"C:\\Users\\FrancescoGeri\\Documents\\Lavori\\eGeos\\satellite2forest\\dataset"

    pathToInf = args.pathInf
    outBasePath = args.pathOut
    outputRaster = args.output
    
    inferencePath=os.path.dirname(pathToInf)
    inferences=os.path.basename(pathToInf)

    rasters=args.tile.split(',')

    overWrite = True

    # rasters_l1 = ['32TQM','33TUG','32TQN','32TPM','33TVG','33TUF','33TVF','32TNN','32TPN','33TUH','33TVH','32TNP','32TPP',
    #               '32TQP','33TUJ','32TNQ','32TPQ','32TQQ']
    # rasters_l2 = ['32TLP','32TMP','32TLQ','32TMQ','32TLR','32TMR','32TNR','32TPR','32TQR','33TUL','33TVL','32TLS','32TMS',
    #               '32TNS','32TPS','32TQS','33TUM','32TPT','32TQT']
    # rasters_l3 = ['33TWG','33TWF','33TXF','33TYF','33TVE','33TWE','33TXE','33TYE','33SWD','33SXD','33STC','33SUC','33SVC',
    #               '33SWC','33SXC','33STB','33SUB','33SVB','33SWB','32SQF','33SVA','33SWA','33STV','32TML','32TNL','32TMK',
    #               '32TNK','32SMJ','32SNJ']

    # rasters = ['32TQM']
    # rasters = ['32TQM','33TUG','32TQN','32TPM']
    # rasters = ['33TVG','33TUF','33TVF','32TNN']
    # rasters = ['32TPN','33TUH','33TVH','32TNP']

    with arcpy.da.SearchCursor (tiles, ['Lotto', 'Name'], sql_clause=("", "ORDER BY Lotto, Name"))as cursor:
        for row in cursor:

            if not row[1] in rasters:
                continue


            arcpy.env.workspace = inferencePath
            #inferences = arcpy.ListRasters(f"*{row[1]}*", "TIF")
            #inferences = ['32TQM_inference_20230101.tif']
            arcpy.ClearEnvironment("workspace")

            # if len(inferences) == 0:
            #     continue

            outPath = os.path.join(outBasePath, f"{outputRaster}{versione}_{row[0]}")
            outLCC = os.path.join(outPath, f"LC_{row[1]}.tif")

            if arcpy.Exists(outLCC):
                if overWrite:
                    arcpy.management.Delete(outLCC)
                else:
                    continue

            # inference = difflib.get_close_matches(f"CLC_{row[1]}.tif", inferences)[0]
            rasRef = os.path.join(inferencePath, inferences)

            #ipdb.set_trace()

            createLCC(gdb, dataset, rasRef, outPath, f"{row[1]}").run()

