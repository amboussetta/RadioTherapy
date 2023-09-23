#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  1 13:08:24 2023

@author: kobr0v
"""

import dicom_contour.contour as dc
import dicom, pydicom
from dicompylercore import dicomparser, dvh, dvhcalc
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import numpy as np
from functools import reduce
from math import dist


def get_StructureIdName(Structure_file):
    ID_dict = dict()
    for structure in list(RS_structures.values()):
        ID_dict[structure['name']]=structure['id']
    return ID_dict

def unique(lists):
       unique_values = reduce(lambda x, y: x + [y] if y not in x else x, lists, [])
       return unique_values

def all_member(struct_list):
    final_list=[]
    if not struct_list:
        print("No structure found")
        return []
    elif len(struct_list)==1:
        final_list = list(set(struct_list[0]))
    else:
        for i in range(1,len(struct_list)):
            final_list.append(list(set(struct_list[i-1]) | set(struct_list[i])))
    #flat_list = list(set(final_list))
    flat_list = [item for sublist in final_list for item in sublist]
    unique_list = unique(flat_list)
    return sorted(unique_list)

def common_member(a, b):
    common_z =[]
    a_set = set(a)
    b_set = set(b)
 
    if (a_set & b_set):
        common_z = list(a_set & b_set)
        return common_z
    else:
        print("No common z")
        
def polygon_union_coord(polygon_list):
    multiPolygonFlag = False
    if len(polygon_list)==0:
        print("no polygon in list")
    elif len(polygon_list)==1:
        return multiPolygonFlag, list(polygon_list[0].exterior.coords)
    else:
        temp = unary_union(polygon_list)
        #temp = polygon_list[0]
        #for i in range(1,len(polygon_list)):
            #temp = temp.union(polygon_list[i])
        if temp.geom_type == 'Polygon':
            coords = list(temp.exterior.coords)
        else:
            multiPolygonFlag = True
            coords = [list(item.exterior.coords) for item in temp.geoms] 
            #print("Check the coords in multi polygon:    ",coords)
            
    return multiPolygonFlag, coords       

def structure_union(struct_list):
    coord_dict = dict()
    all_z = all_member(struct_list)
    #print("all_z:   ",all_z)
    for z in all_z:
        #print("z:    ",z)
        polygons =[]
        for structure in struct_list:
            #print("Structure ID:    ",structure.keys())
            if z not in list(structure.keys()):
                #print(z," = z not found in structure")
                continue
            planes = structure[z]
            for contour in planes:
                structure2D = []
                for x,y,zz in contour["data"]:
                    structure2D.append((x,y))
                polygon = Polygon(structure2D)
                polygons.append(polygon)
        #print("polygon list length:     ",len(polygons))
        flag, coord_union_z = polygon_union_coord(polygons)
        if flag== False:
            coord_union_z = [list(var) for var in coord_union_z]
            for xy in coord_union_z:
                    xy.append(float(z))
            data_dict =dict()
            data_dict["type"]='CLOSED_PLANAR'
            data_dict["data"]=coord_union_z
            coord_dict[z]= [data_dict]
        else:
            coord_union_z = [[list(var) for var in item] for item in coord_union_z]
            data_dict_list=[]
            for element in coord_union_z:
                for xy in element:
                    xy.append(float(z))
                data_dict =dict()
                data_dict["type"]='CLOSED_PLANAR'
                data_dict["data"]=element
                data_dict_list.append(data_dict)
            coord_dict[z]= data_dict_list
    return coord_dict

def calculate_volume(coord_dict, thickness):
    surfaces=[]
    for z in coord_dict.keys():
        for contour in coord_dict[z]:
            coord2D=[]
            for x,y,zz in contour["data"]:
                coord2D.append((x,y))
            polygon = Polygon(coord2D)
            area = polygon.area
            surfaces.append(area) 
    volume =  sum(surfaces) *thickness /1000
    return volume

def calculate_overlap(coord_A, coord_B, thickness):
    surfaces = []
    common_z = common_member(coord_A.keys(), coord_B.keys())
    for z in common_z:
        coord_dictA = coord_A[z]
        coord_dictB = coord_B[z]
        polygonsA = []
        polygonsB = []
        for contour in coord_dictA:
            coord2D=[]
            for x,y,zz in contour["data"]:
                coord2D.append((x,y))
            polygon = Polygon(coord2D)
            polygonsA.append(polygon)
        for contour in coord_dictB:
            coord2D=[]
            for x,y,zz in contour["data"]:
                coord2D.append((x,y))
            polygon = Polygon(coord2D)
            polygonsB.append(polygon)
        for i in polygonsA:
            for j in polygonsB:
                if i.intersects(j):
                    overlap_polygon = i.intersection(j)
                    overlap_area = overlap_polygon.area
                    surfaces.append(overlap_area)
    volume =  sum(surfaces) *thickness /1000
    return volume

def calculate_barycentric_coords(coords):
    all_z= list(coords.keys())
    coord3D=[]
    for z in all_z:
        planes_centroids = []
        for contour in coords[z]:
            coord3Dz=[]
            for x,y,zz in contour["data"]:
                coord3Dz.append([x,y,z])
            poly = Polygon(coord3Dz)
            planes_centroids.append(poly.centroid)
        if len(planes_centroids)>1:
            centroid_line = LineString(planes_centroids)
            coord3D.append([centroid_line.centroid.x, centroid_line.centroid.y, z])
        else:
            coord3D.append([planes_centroids[0].x, planes_centroids[0].y, z])                
    coord3D = [list(map(float, sublist)) for sublist in coord3D]
    barycenter = [sum(sub_list) / len(sub_list) for sub_list in zip(*coord3D)]
    return barycenter

def calculate_barycentric_distance(coordA, coordB):
    barycenterA = np.array(calculate_barycentric_coords(coordA))
    barycenterB = np.array(calculate_barycentric_coords(coordB))
    squared_dist = np.sum((barycenterA-barycenterB)**2, axis=0)
    distance = np.sqrt(squared_dist)
    return distance/10

def calculate_distance_centroid(coord_A, coord_B):
    all_za = coord_A.keys()
    all_zb = coord_B.keys()
    LineA_list =[]
    LineB_list = []
    for z in all_za:
        coord_dictA = coord_A[z]
        centroidA = []
        for contour in coord_dictA:
            coord2D=[]
            for x,y,zz in contour["data"]:
                coord2D.append((x,y))
            polygon = Polygon(coord2D)
            centroidA.append(polygon.centroid)
        if len(centroidA)>1:
            LineA = LineString(centroidA)
            LineA_list.append(LineA.centroid)
        else:
            LineA_list.append(centroidA[0])
    for z in all_zb:
        coord_dictB= coord_B[z]
        centroidB = []
        for contour in coord_dictB:
            coord2D=[]
            for x,y,zz in contour["data"]:
                coord2D.append((x,y))
            polygon = Polygon(coord2D)
            centroidB.append(polygon.centroid)
        if len(centroidB)>1:
            LineB = LineString(centroidB)
            LineB_list.append(LineB.centroid)
        else:
            LineB_list.append(centroidB[0])
    LineA = LineString(LineA_list)
    LineB= LineString(LineB_list)
    CenterA = LineA.centroid
    CenterB = LineB.centroid
    distance = CenterA.distance(CenterB)
    return distance/10

def get_structuresData(ListOfStructures, StructureIdName_dict, dicomparserOption):
    Structures_data = dict()
    for structure in ListOfStructures:
        if structure == 'PTV':
            temp = dict()
            id_struct = 00
            temp['id'] = id_struct
            ListOfCoordinatesPTVUnion = [Structures_data[element]['coords'] for element in PTV]
            coord_ptv = structure_union(ListOfCoordinatesPTVUnion)
            temp['coords'] = coord_ptv
            temp['thickness'] = round(dp.CalculatePlaneThickness(temp['coords']),1)
            if dicomparserOption == True:
                temp['volume'] = dp.CalculateStructureVolume(temp['coords'],temp['thickness'])
            else:
                temp['volume'] = calculate_volume(temp['coords'],temp['thickness'])
            Structures_data[structure] = temp
        else:
            temp = dict()
            id_struct = StructureIdName_dict[structure]
            temp['id'] = id_struct
            temp['coords'] = dp.GetStructureCoordinates(id_struct)
            temp['thickness'] = round(dp.CalculatePlaneThickness(temp['coords']),1)
            if dicomparserOption == True:
                temp['volume'] = dp.CalculateStructureVolume(temp['coords'],temp['thickness'])
            else:
                temp['volume'] = calculate_volume(temp['coords'],temp['thickness'])
            Structures_data[structure] = temp
    return Structures_data



print("##########################Testing Results ################################")
print("##################################################################")
print("##################################################################")
print("##################################################################")
print("##################################################################")



dp = dicomparser.DicomParser("RS.1.2.246.352.205.5649099458074933255.8645308473566043272.dcm")
RS_structures = dp.GetStructures()


# Please define the PTV structure
PTV = ['PTV46', 'PTV46VS', 'PTV76']

# Please place 'PTV' at the end of the list
ListOfStructures = ['dig', 'vessie', 'Rectum', 'dig', 'PTV46', 'PTV46VS', 'PTV76', 'PTV']

Structures_data = get_structuresData(ListOfStructures,get_StructureIdName(RS_structures), False)
for element in Structures_data.keys():
    print("Name:", element, "thickness:", Structures_data[element]["thickness"], "Volume:", Structures_data[element]["volume"])
  

print("dig vs PTV46 Total:      distance: ", calculate_overlap(Structures_data["dig"]["coords"],\
                                    Structures_data["PTV"]["coords"], Structures_data["PTV"]["thickness"])\
    ,'distance' , calculate_distance_centroid(Structures_data["dig"]["coords"],Structures_data["PTV"]["coords"]))

print("Rectum vs PTV76:      distance: ", calculate_overlap(Structures_data["Rectum"]["coords"],\
                                    Structures_data["PTV76"]["coords"], Structures_data["PTV76"]["thickness"])\
    ,'distance' , calculate_distance_centroid(Structures_data["Rectum"]["coords"],Structures_data["PTV76"]["coords"]))
                                                                        

print("Vessie vs PTV76:      distance: ", calculate_overlap(Structures_data["vessie"]["coords"],\
                                    Structures_data["PTV76"]["coords"], Structures_data["PTV76"]["thickness"])\
    ,'distance' , calculate_distance_centroid(Structures_data["vessie"]["coords"],Structures_data["PTV76"]["coords"]))


print("Barycentric distance between dig and PTV ", calculate_barycentric_distance(Structures_data["dig"]["coords"], Structures_data["PTV"]["coords"]))

# print("####################@ TOY EXAMPLE #########################@@")


# dict1 =dict()
# coord_dict1 = dict()
# dict1["data"]=[[20, 20, 10], [60, 20, 10], [60, 40, 10], [20, 40, 10]]
# dict1["type"]='CLOSED_PLANAR'
# coord_dict1['10']= [dict1]

# dict2 =dict()
# coord_dict2 = dict()
# dict2["data"]=[[40, 30, 10], [40, 70, 10], [80, 70, 10], [70, 30, 10]]
# dict2["type"]='CLOSED_PLANAR'
# coord_dict2['10']= [dict2]


# coord_union = structure_union([coord_dict2,coord_dict1])


# poly_1 =  Polygon([(20, 20), (60, 20), (60, 40), (20, 40)])
# poly_2 =  Polygon([(40, 30), (40, 70), (80, 70), (70, 30)])
# poly=unary_union([poly_1,poly_2])


# poly_bis = Polygon([(60.0, 20.0), (20.0, 20.0), (20.0, 40.0), (40.0, 40.0), (40.0, 70.0), 
#                     (80.0, 70.0), (70.0, 30.0), (60.0, 30.0), (60.0, 20.0)])
# poly_inter = poly_1.intersection(poly_2)

# volume = calculate_volume(coord_union, 1)*1000

# print(volume)
# print(poly_bis.area)
# print(poly.area)

# print(poly_1.area  + poly_2.area - poly_inter.area)

# print(coord_union)

# print(list(poly.exterior.coords))