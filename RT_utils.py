import dicom, pydicom
from dicompylercore import dose
from dicompylercore import dicomparser, dvh, dvhcalc
import os
import pandas as pd
import numpy as np
from geometric_utils import get_StructureIdName, calculate_volume


def get_structuresData(ListOfStructures, rtstructure, StructureIdName_dict, structure_equivalents, dicomparserOption):
    id_struct = "empty"
    Structures_data = dict()
    new_dict_structures = dict()
    for structure in ListOfStructures:
        firstequivalent_flag = True
        found = False
        if structure == 'PTV_constructed':
            temp = dict()
            id_struct = 00
            temp['id'] = id_struct
            #ListOfCoordinatesPTVUnion = [Structures_data[element]["coords"] for element in PTV_constructed]
            ListOfCoordinatesPTVUnion = [rtstructure.GetStructureCoordinates(StructureIdName_dict[element]) for element in PTV_constructed]
            coord_ptv = structure_union(ListOfCoordinatesPTVUnion)
            temp['coords'] = coord_ptv
            temp['thickness'] = round(rtstructure.CalculatePlaneThickness(temp['coords']),1)
            if dicomparserOption == True:
                temp['volume'] = rtstructure.CalculateStructureVolume(temp['coords'],temp['thickness'])
            else:
                temp['volume'] = calculate_volume(temp['coords'],temp['thickness'])
            Structures_data[structure] = temp
        else:
            temp = dict()
            if structure not in StructureIdName_dict.keys():
                if structure in structure_equivalents.keys():
                    firstequivalent_flag = False
                    for name in structure_equivalents[structure]:
                            if name in StructureIdName_dict.keys():
                                id_struct = StructureIdName_dict[name]
                                print("This is the PTV nomenclature used for this patient" )
                                print(name)
                                found = True
                                new_dict_structures[structure] = name
                                break 
                if found == False:  
                    print("Unable to find the structure:  ", structure )
                    print("This is the set of names available in this file:")
                    print(StructureIdName_dict.keys())
                    equiv_struct =""
                    while equiv_struct not in StructureIdName_dict.keys():
                        equiv_struct = input("Please enter its equivalent name:  ")
                    if firstequivalent_flag == True:    
                        structure_equivalents[structure] = [equiv_struct]
                    else:
                        structure_equivalents[structure].append(equiv_struct) 
                    for name in structure_equivalents[structure]:
                            if name in StructureIdName_dict.keys():
                                id_struct = StructureIdName_dict[name]
                                new_dict_structures[structure] = name
                                break 
            else:  
                id_struct = StructureIdName_dict[structure]
                new_dict_structures[structure] = structure
                
            print("#####################################")
            #if id_struct != "empty":
               ## print("Structure ID correctly obtained!")
           # else:
               # print("Structure ID not available!")
                
            temp['id'] = id_struct
            temp['coords'] = rtstructure.GetStructureCoordinates(id_struct)
            #if not list(temp['coords'].values()):
               # print(temp['coords'])
            #else:
                #print(list(temp['coords'].values())[0])
            temp['thickness'] = rtstructure.CalculatePlaneThickness(temp['coords'])
            #print("id: ", id_struct, "  thickness:  ", temp['thickness'])
            if dicomparserOption == True:
                temp['volume'] = rtstructure.CalculateStructureVolume(temp['coords'],temp['thickness'])
            else:
                temp['volume'] = calculate_volume(temp['coords'],temp['thickness'])
                
           # print("Volume =  ", temp['volume'])
            Structures_data[structure] = temp
    return Structures_data, new_dict_structures


def sum_RTDose(RS_path, RD1_path, RD2_path):
     ### Checking the order of RD files (Plan 1 vs Plan 2)
        #digdvh1 = dvhcalc.get_dvh(RS_path, RD1_path, get_StructureIdName(RS_structures)['dig'])
        digdvh1 = dvhcalc.get_dvh(RS_path, RD1_path, 1)
        digdvh2 = dvhcalc.get_dvh(RS_path, RD2_path, 1)
        if digdvh2.max > digdvh1.max:
            print("Switching RD1 and RD2 files to correspond with plan treatements")
            temp_path = RD2_path
            RD2_path = RD1_path
            RD1_path = temp_path
        
        #Creating rtdose for total ptv
        rt_dose1 = pydicom.dcmread(RD1_path)
        rt_dose2 = pydicom.dcmread(RD2_path)
        dose_array1 = rt_dose1.pixel_array * rt_dose1.DoseGridScaling
        dose_array2 = rt_dose2.pixel_array * rt_dose2.DoseGridScaling
        if dose_array1.shape != dose_array2.shape:
            dx, dy, dz = dose_array1.shape
            dxx, dyy, dzz = dose_array2.shape
            xmax, ymax, zmax = (max(dx,dxx), max(dy,dyy), max(dz,dzz))
            dose_array1 = np.pad(dose_array1, ((0,xmax-dx), (0,ymax-dy), (0, zmax-dz)), 'constant')
            dose_array2 = np.pad(dose_array2, ((0,xmax-dxx), (0,ymax-dyy), (0, zmax-dzz)), 'constant')
            print("printing shapes of dose arrays: ")
            print(dose_array1.shape,dose_array2.shape)
        
        sum_dcm = rt_dose1
        sumx = dose_array1 + dose_array2
        sum_scaling = np.max(sumx) / (2 ** int(rt_dose1.HighBit))
        sumx = sumx/sum_scaling
        sumx = np.uint32(sumx)

        #sum_dcm.pixel_array = sum
        sum_dcm.BitsAllocated = 32
        sum_dcm.BitsStored = 32
        sum_dcm.HighBit = 31
        sum_dcm.PixelData = sumx.tobytes()
        sum_dcm.DoseGridScaling = sum_scaling
        sum_dcm.DoseSummationType = "MULTI_PLAN"
        sum_dcm.DoseComment = "Summed Dose"

        #packed = np.packbits(new_dose_data).tobytes()
        #new_dose_data = packed + b'\x00' if len(packed) % 2 else packed
        #rtdose_tot.PixelData = new_dose_data

        return sum_dcm