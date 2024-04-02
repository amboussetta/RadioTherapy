#importing standard libraries
import dicom_contour.contour as dc
import dicom, pydicom
from dicompylercore import dose
from dicompylercore import dicomparser, dvh, dvhcalc
from shapely.geometry import Point, Polygon, LineString
from shapely.geometry.base import BaseGeometry, BaseMultipartGeometry
import math
from typing import Tuple
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
import os, pandas as pd
import copy
import matplotlib.pyplot as py
import seaborn as sns
import pymedphys

#importing internal modules
from geometric_utils import *
from RT_utils import *

### Construct databse from patients' files
directory = "/Users/kobr0v/Documents/Cleverlytics/CFJ Radio/Patient files 3"

#Create database dataframes
Excel_database_dig = pd.DataFrame(columns=['Vol dig', 'Vol PTV46', 'Overlap Vol', 'OV/Vdig', 'Centroid distance', 'Borders distance', 'Distance to ves', 'Distance to rec','V5', 'V15', 'V30', 'V45', 'V45_plan 1', 'V45_plan2', 'Dmoy'])
Excel_database_rec = pd.DataFrame(columns=['Vol rec', 'Vol PTV76', 'Overlap Vol', 'OV/Vrec', 'Distance', 'V5', 'V15', 'V30', 'V45', 'V60 %', 'V70 %', 'Dmoy', 'Dmax'])
Excel_database_ves = pd.DataFrame(columns=['Vol ves', 'Vol PTV76', 'Overlap Vol', 'OV/Vves', 'Distance', 'V5', 'V15', 'V30', 'V45', 'V60 %', 'V70 %', 'Dmoy', 'Dmax'])

DigCorr_database = pd.DataFrame(columns=['Vol dig', 'Overlap PTV46', 'OV/Vdig', 'Distance', 'V45', 'Dmoy'])
RecCorr_database = pd.DataFrame(columns=['Vol rectum', 'Overlap PTV76', 'OV/Vrec', 'Distance', 'V70' ,'Dmoy'])
VesCorr_database = pd.DataFrame(columns=['Vol vessie', 'Overlap PTV76', 'OV/Vves', 'Distance', 'V70', 'Dmoy'])


counter = 0
#Do the next computations for every patient (subdirectory) in the folder
for subdirectory in os.listdir(directory):
    new_dict_structures = dict()
    counter = counter +1 
    # if subdirectory != "20221166":
    #     continue
    
    if not subdirectory.startswith('.'):
        #PTV = []
        RS_filename=""
        RD_filename="" 
        RD2_filename=""
        patient_folder = os.path.join(directory, subdirectory)
        RD1_flag = False
        for filename in os.listdir(patient_folder):
            if not filename.startswith('.'):
                #print(filename)
                if "RS" in filename:
                    RS_filename = filename
                if "RD" in filename and RD1_flag == False:
                    RD_filename = filename
                    RD1_flag = True
                elif "RD" in filename and RD1_flag == True:
                    RD2_filename = filename
                else:
                    continue
        RS_path =os.path.join(directory, subdirectory, RS_filename)
        RD1_path = os.path.join(directory, subdirectory, RD_filename)
        RD2_path =  os.path.join(directory, subdirectory, RD2_filename)
        rtstructure = dicomparser.DicomParser(RS_path)
        RS_structures = rtstructure.GetStructures()
        # rtdose1 = dicomparser.DicomParser(RD1_path)
        # rtdose2 = dicomparser.DicomParser(RD2_path)

        # Compute the sum of the two RT Dose files
        sum_dcm = sum_RTDose(RS_path, RD1_path, RD2_path)
        RD_total_path = os.path.join(directory, subdirectory, "Total_dose")
        sum_dcm.save_as(RD_total_path)

        
        # Definition of PTV
        PTV_constructed = ['PTV46x', 'PTV76x']
        
        # Please define the list of structures for analysis. Put at the end of the 'ListOfStructures' list:
        # + 'PTV_constructed' to construct the global ptv using the union of structures inside PTV_constructed list
        # + 'PTV46x' to ask the user to type the equivalent name of the global ptv46
        # + 'PTV76x' to ask the user to type the equivalent name of the global ptv76
        # + 'PTV' to automatically select the equivalent nomenclature from the PTV list  
        # Please define PTV global equivalent nomenclatures
        PTV = ['Z-PTV GLOBAL', 'ZPTV46 TOT', 'Z PTV GLOBAL', 'Z TEST PTV 46', 'PTVT', 'ZPTV 46 TOT', 'PTV_TOT46', 'PTV 46', 'PTV T', 'Z-PTV GLOBAL', 'Z-PTV46 GLOBAL', 'PTV46 HDV', 'PTV46T', 'Zz PTV46', 'PTV GLOBAL' ]

        ListOfStructures = ['dig', 'vessie', 'Rectum', 'PTV46x', 'PTV76x']

        print(subdirectory, RS_filename)
        print(subdirectory, RD2_filename) 

        StructureIdName_dict = get_StructureIdName(RS_structures)

        #Select the excel file containing nomenclature equivalence
        listptv46 = pd.read_excel('nomenclature.xlsx', sheet_name='PTV46')
        listptv76 = pd.read_excel('nomenclature.xlsx', sheet_name='PTV76') # can also index sheet by name or fetch all sheets
        mylist46 = listptv46['PTV46'].tolist() 
        mylist76 = listptv76['PTV76'].tolist()
        #structure_equivalents = {'PTV46x': ['Z-PTV GLOBAL','z- PTV GLOBAL', 'PTV_TOT46','PTV46 TOTAL', 'Z-PTV46 GLOBAL', 'PTV46T', 'PTVT', 'PTV46 HDV', 'PTV 46','PTV 46 T' , 'z PTV46','z_PTV46','zPTV46T','z_PTV45','PTV46 HDV', 'PTV46 HDVnew', 'ZPTV 46 TOT', 'PTV T', 'PTVt', 'Z TEST PTV 46', 'Z PTV GLOBAL', 'Z PTV TOTAL'], 'PTV76x': ['PTV P 76', 'PTV76', 'z PTV76 opt', 'PTV 74']}
        structure_equivalents = {'PTV46x': mylist46, 'PTV76x': mylist76}

        Structures_data, new_dict_structures = get_structuresData(ListOfStructures, rtstructure, StructureIdName_dict, structure_equivalents, False) 

        digdvh = dvhcalc.get_dvh(RS_path, RD_total_path, StructureIdName_dict[new_dict_structures['dig']])
        digdvh1 = dvhcalc.get_dvh(RS_path, RD1_path, StructureIdName_dict[new_dict_structures['dig']])
        digdvh2 = dvhcalc.get_dvh(RS_path, RD2_path, StructureIdName_dict[new_dict_structures['dig']])
        recdvh = dvhcalc.get_dvh(RS_path, RD_total_path, StructureIdName_dict[new_dict_structures['Rectum']])
        #recdvh2 = dvhcalc.get_dvh(RS_path, RD2_path, get_StructureIdName(RS_structures)['Rectum'])
        vesdvh = dvhcalc.get_dvh(RS_path, RD_total_path, StructureIdName_dict[new_dict_structures['vessie']])
        #vesdvh2 = dvhcalc.get_dvh(RS_path, RD2_path, get_StructureIdName(RS_structures)['vessie'])
        #digdvhtotal = dvhcalc.get_dvh(RS_path, RD_total_path, get_StructureIdName(RS_structures)['dig'])
        
        Vol_dig =Structures_data['dig']["volume"]
        Vol_rec =Structures_data['Rectum']["volume"]
        Vol_ves =Structures_data['vessie']["volume"]
        Vol_PTV46 =Structures_data['PTV46x']["volume"]
        Vol_PTV76 =Structures_data['PTV76x']["volume"]
        #Vol_PTV =Structures_data['PTV_constructed']["volume"]
        
    
        
        #Overlap_dig = calculate_overlap(Structures_data["dig"]["coords"],\
         #                                 Structures_data["PTV_constructed"]["coords"], Structures_data["PTV_constructed"]["thickness"])
        Overlap_dig46 = calculate_overlap(Structures_data["dig"]["coords"],\
                                          Structures_data["PTV46x"]["coords"], Structures_data["PTV46x"]["thickness"])
        Overlap_rec76 = calculate_overlap(Structures_data["Rectum"]["coords"],\
                                          Structures_data["PTV76x"]["coords"], Structures_data["PTV76x"]["thickness"])
        Overlap_ves76 = calculate_overlap(Structures_data["vessie"]["coords"],\
                                          Structures_data["PTV76x"]["coords"], Structures_data["PTV76x"]["thickness"])
            
        #Distance_dig = calculate_distance_centroid(Structures_data["dig"]["coords"],Structures_data["PTV_constructed"]["coords"])
        Distance_dig46 = calculate_barycentric_distance(Structures_data["dig"]["coords"],Structures_data["PTV46x"]["coords"])
        Distance_borders_dig46 = calculate_borders_distance(Structures_data["dig"]["coords"],Structures_data["PTV46x"]["coords"])
        Distance_digves = calculate_barycentric_distance(Structures_data["dig"]["coords"],Structures_data["vessie"]["coords"])
        Distance_digrec = calculate_barycentric_distance(Structures_data["dig"]["coords"],Structures_data["Rectum"]["coords"])
        
        Distance_rec76 = calculate_barycentric_distance(Structures_data["Rectum"]["coords"],Structures_data["PTV76x"]["coords"])
        Distance_ves76 = calculate_barycentric_distance(Structures_data["vessie"]["coords"],Structures_data["PTV76x"]["coords"])
        
        
        #V45_dig_1 = digdvh1.statistic("V45Gy").value
        V5_dig = digdvh.statistic("V5Gy").value
        V15_dig = digdvh.statistic("V15Gy").value
        V30_dig = digdvh.statistic("V30Gy").value
        V45_dig = digdvh.statistic("V45Gy").value
        V45_plan1 =digdvh1.statistic("V45Gy").value
        V45_plan2 =digdvh2.statistic("V45Gy").value
        
        V5_rec = recdvh.statistic("V5Gy").value
        V15_rec = recdvh.statistic("V15Gy").value
        V30_rec = recdvh.statistic("V30Gy").value
        V45_rec = recdvh.statistic("V45Gy").value
        V60_rec = recdvh.statistic("V60Gy").value
        V70_rec = recdvh.statistic("V70Gy").value
        
        V5_ves = vesdvh.statistic("V5Gy").value
        V15_ves = vesdvh.statistic("V15Gy").value
        V30_ves = vesdvh.statistic("V30Gy").value
        V45_ves = vesdvh.statistic("V45Gy").value
        V60_ves = vesdvh.statistic("V60Gy").value
        V70_ves = vesdvh.statistic("V70Gy").value
        

        Dmoy_dig = digdvh.mean
        Dmoy_rec = recdvh.mean
        Dmoy_ves = vesdvh.mean
        Dmax_rec = recdvh.max
        Dmax_ves = vesdvh.max
        
        #Debugging patient 20221203
        # if subdirectory=="20221166":
        #     digdvh1 = dvhcalc.get_dvh(RS_path, RD1_path, get_StructureIdName(RS_structures)['dig'])
        #     digdvh2 = dvhcalc.get_dvh(RS_path, RD2_path, get_StructureIdName(RS_structures)['dig'])
        #     V15_dig_1 = digdvh1.statistic("V15Gy").value
        #     V05_dig_1 = digdvh1.statistic("V0.5Gy").value
        #     V15_dig_2 = digdvh2.statistic("V15Gy").value
        #     V05_dig_2 = digdvh2.statistic("V0.5Gy").value
        #     V45_dig_1 = digdvh1.statistic("V45Gy").value
        #     V45_dig_2 = digdvh2.statistic("V45Gy").value
        #     V15_dig = digdvh.statistic("V15Gy").value
        #     V05_dig = digdvh.statistic("V0.5Gy").value
        #     V45_dig = digdvh.statistic("V45Gy").value
        #     print("===========Debugging patient 20221166 ============")
        #     print("RD1 ===> " + "V0.5: ", V05_dig_1,", V15: ", V15_dig_1, ", V45: ", V45_dig_1)
        #     print("RD2 ===> " + "V0.5: ", V05_dig_2,", V15: ", V15_dig_2, ", V45: ", V45_dig_2)
        #     print("RDT ===> " + "V0.5: ", V05_dig,", V15: ", V15_dig, ", V45: ", V45_dig)
           
        #     print("===========Debugging patient 20221166 ============")

        Excel_database_dig.loc[subdirectory] = [Vol_dig, Vol_PTV46, Overlap_dig46, Overlap_dig46/Vol_dig, Distance_dig46, Distance_borders_dig46, Distance_digves, Distance_digrec, V5_dig, V15_dig, V30_dig, V45_dig, V45_plan1, V45_plan2, Dmoy_dig]
        Excel_database_rec.loc[subdirectory] = [Vol_rec, Vol_PTV76, Overlap_rec76, Overlap_rec76/Vol_rec, Distance_rec76, V5_rec, V15_rec, V30_rec, V45_rec, V60_rec/Vol_rec, V70_rec/Vol_rec, Dmoy_rec, Dmax_rec]
        Excel_database_ves.loc[subdirectory] = [Vol_ves, Vol_PTV76, Overlap_ves76, Overlap_ves76/Vol_ves, Distance_ves76, V5_ves, V15_ves, V30_ves, V45_ves, V60_ves/Vol_ves, V70_ves/Vol_ves, Dmoy_ves, Dmax_ves]

#write the databases into a single Excel file        
with pd.ExcelWriter('large_database.xlsx') as writer:  
    Excel_database_dig.to_excel(writer, sheet_name="dig")
    Excel_database_rec.to_excel(writer, sheet_name="rectum")
    Excel_database_ves.to_excel(writer, sheet_name="vessie")
    
# DigCorr_database.loc[subdirectory] = [Vol_dig, Overlap_dig46, Overlap_dig46/Vol_dig, Distance_dig46, V45_dig, Dmoy_dig]
# RecCorr_database.loc[subdirectory] = [Vol_rec, Overlap_rec76, Overlap_rec76/Vol_rec, Distance_rec76, V70_rec, Dmoy_rec]
# VesCorr_database.loc[subdirectory] = [Vol_ves, Overlap_ves76, Overlap_ves76/Vol_ves, Distance_ves76, V70_ves, Dmoy_ves]
        
        
        
#print(Excel_database)
#sns.pairplot(data=database)
    

