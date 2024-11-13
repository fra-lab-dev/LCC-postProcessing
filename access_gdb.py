## lettura gdb con fiona e geopandas

import geopandas as gpd
import fiona

file_gdb="C:\\Users\\FrancescoGeri\\Downloads\\DBNS_test\\DBNS_test.gdb"

#Print them
for f_class in fiona.listlayers(file_geodatabase):
    print(feature_class)
    
'''ancillary
RulesOrdineCaricamento
RulesXmatch
Tiles
Tiles_NoOverlap
MaskMare
LimReg
ait
ait_l
region'''


df=gpd.read_file(filename=file_gdb, layer="Tiles")

print(df)

'''
     Name  Lotto  ...  Shape_Area                                           geometry
0   32SMJ      3  ...    1.259036  MULTIPOLYGON Z (((7.83238 39.74440 0.00000, 9....
1   32SNJ      3  ...    1.258996  MULTIPOLYGON Z (((8.99977 39.75027 0.00000, 10...
2   32SQF      3  ...    1.211960  MULTIPOLYGON Z (((11.24793 37.02528 0.00000, 1...
3   32TLP      2  ...    1.347485  MULTIPOLYGON Z (((6.49593 44.22596 0.00000, 7....
4   32TLQ      2  ...    1.367937  MULTIPOLYGON Z (((6.45686 45.12551 0.00000, 7....
..    ...    ...  ...         ...                                                ...
61  33TYF      3  ...    1.289609  MULTIPOLYGON Z (((17.39670 41.52686 0.00000, 1...
62  32TPT      2  ...    1.435256  MULTIPOLYGON Z (((10.33660 47.84592 0.00000, 1...
63  32TQT      2  ...    1.432973  MULTIPOLYGON Z (((11.67154 47.82261 0.00000, 1...
64  33SWA      3  ...    1.214312  MULTIPOLYGON Z (((14.99978 37.04658 0.00000, 1...
65  33TVL      2  ...    1.390344  MULTIPOLYGON Z (((13.70695 46.04626 0.00000, 1...

[66 rows x 5 columns]
'''
