# Dose prediction models for radiotherapy

## Introduction
We present in this project a simple methodology to predict dose-volume histogram of a patient given its RT Structure file (RS). 
In main.py, we construct a dataset from RS and RT Dose (RD) files containing a set of geometric features and different markers of the dose-volume histogram (V5, V10, V15, etc.)
using our set of functions in the modules geometric_utils.py and RT_utils.py. Finally, we train and test different machine learning (ML) models and compare their performance
using adequate metrics.

## Installation
Best way to test or collaborate on the project is to:
1. Create a fork into your own github repo
2. Clone the forked repo into your local machine
3. Experiment with your local copy
4. Add, Commit and Push any useful modifications 
5. (Optional) Initiate a pull request if you wish to contribute directly to this repository


The following modifications for a quick hands-on all happen in the main.py file

#### Changing directory paths
Paths should be modifed according to your file organization. First, modify the path to your patients folder:
```python
directory = "/Users/kobr0v/Documents/Cleverlytics/CFJ Radio/Patient files 3"
```
#### Restructuring the columns of the databases
You can add features in existing databases, or add new databases in what follows:
```python
#Create database dataframes
Excel_database_dig = pd.DataFrame(columns=['Vol dig', 'Vol PTV46', 'Overlap Vol', 'OV/Vdig', 'Centroid distance', 'Borders distance', 'Distance to ves', 'Distance to rec','V5', 'V15', 'V30', 'V45', 'V45_plan 1', 'V45_plan2', 'Dmoy'])
Excel_database_rec = pd.DataFrame(columns=['Vol rec', 'Vol PTV76', 'Overlap Vol', 'OV/Vrec', 'Distance', 'V5', 'V15', 'V30', 'V45', 'V60 %', 'V70 %', 'Dmoy', 'Dmax'])
Excel_database_ves = pd.DataFrame(columns=['Vol ves', 'Vol PTV76', 'Overlap Vol', 'OV/Vves', 'Distance', 'V5', 'V15', 'V30', 'V45', 'V60 %', 'V70 %', 'Dmoy', 'Dmax'])
```

#### PTV definition method
The planning target volume (PTV) can be directly defined as the union of multiple structures inside the variable PTV, 
or it can be constructed from a predefined PTV structure in the RS file. In this case, we use the variavle PTV_constructed. 
```python
# Definition of PTV
        PTV_constructed = ['PTV46x', 'PTV76x']
        
        # Please define the list of structures for analysis. Put at the end of the 'ListOfStructures' list:
        # + 'PTV_constructed' to construct the global ptv using the union of structures inside PTV_constructed list
        # + 'PTV46x' to ask the user to type the equivalent name of the global ptv46
        # + 'PTV76x' to ask the user to type the equivalent name of the global ptv76
        # + 'PTV' to automatically select the equivalent nomenclature from the PTV list  
        # Please define PTV global equivalent nomenclatures
        PTV = ['Z-PTV GLOBAL', 'ZPTV46 TOT', 'Z PTV GLOBAL', 'Z TEST PTV 46', 'PTVT', 'ZPTV 46 TOT', 'PTV_TOT46', 'PTV 46', 'PTV T' ]
```

Note that when nomenclature does not match with the one in the RS file, the user is asked to identify the equivalent nomenclature 
from a predefined list. For instance, 'Dig' may be written as 'dig' or 'CavDigestive'. 

#### Choosing the list of structures to analyze and put in the global database
In the variable ListOfStrutures, we list all the structures (organ names) to be analyzed by the program.
It is important to let 'PTV' or 'PTV_Constructed' at the very end of the list.
```python
 ListOfStructures = ['dig', 'vessie', 'Rectum', 'PTV46x', 'PTV76x']
```

#### Nomenclature equivalance
If you already have a list of nomenclature equivalence for PTV46 and PTV 76 in an Excel file, you can read them into
listptv46 and listptv76 variables. If other nomenclature mismatches appear on runtime, the user will be asked to correct the names via the console.
```python
#Select the excel file containing nomenclature equivalence
        listptv46 = pd.read_excel('nomenclature.xlsx', sheet_name='PTV46')
        listptv76 = pd.read_excel('nomenclature.xlsx', sheet_name='PTV76') # can also index sheet by name or fetch all sheets
        mylist46 = listptv46['PTV46'].tolist() 
        mylist76 = listptv76['PTV76'].tolist()
        #structure_equivalents = {'PTV46x': ['Z-PTV GLOBAL','z- PTV GLOBAL', 'PTV_TOT46','PTV46 TOTAL', 'Z-PTV46 GLOBAL', 'PTV46T', 'PTVT', 'PTV46 HDV', 'PTV 46','PTV 46 T' , 'z PTV46','z_PTV46','zPTV46T','z_PTV45','PTV46 HDV', 'PTV46 HDVnew', 'ZPTV 46 TOT', 'PTV T', 'PTVt', 'Z TEST PTV 46', 'Z PTV GLOBAL', 'Z PTV TOTAL'], 'PTV76x': ['PTV P 76', 'PTV76', 'z PTV76 opt', 'PTV 74']}
        structure_equivalents = {'PTV46x': mylist46, 'PTV76x': mylist76}
```

#### Writing results to the Excel database:
The following code writes all the dataframes in one single Excel file called 'large_database.xlsx'.
```python
with pd.ExcelWriter('large_database.xlsx') as writer:  
    Excel_database_dig.to_excel(writer, sheet_name="dig")
    Excel_database_rec.to_excel(writer, sheet_name="rectum")
    Excel_database_ves.to_excel(writer, sheet_name="vessie")
```

## ML models to predict DV histograms
In the notebook Model_compare.ipynb, we prepare a train and test datasets using the above database 'large_database.xlsx', 
and we compare the performance of several ML models.

#### Defining train and test datasets
In this code, we identify the columns corresponding to each dataset. Please change them according to your database:
```python
file="large_database.xlsx"
database = pd.read_excel(file, usecols=[1,2,3,4,5,11, 9, 12])
X = pd.read_excel(file, usecols=[1,2,3,4,5])
y = pd.read_excel(file, usecols=[9,11,12])
y1= pd.read_excel(file, usecols=[9])
y2= pd.read_excel(file, usecols=[12])
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, shuffle=True, random_state=20)
y1_train=y_train.iloc[:,0]
y2_train=y_train.iloc[:,2]
y1_test=y_test.iloc[:,0]
y2_test=y_test.iloc[:,2]
```

#### Creating a ML model
You can create your own ML model by preparing a set of additional features, then creating a pipeline that executes multiple transformation and algorithms.
```python
# create feature union
features = []
features.append(('pca', PCA(n_components=3)))
features.append(('select_best', SelectKBest(k=3)))
feature_union = FeatureUnion(features)
# create pipeline
estimators = []
estimators.append(('standardize', StandardScaler()))
estimators.append(('feature_union', feature_union))
estimators.append(('linear_regression', LinearRegression()))
PCR = Pipeline(estimators)
kfold = KFold(n_splits=3)
PCR_results1 = cross_val_score(PCR, X, y1, cv=kfold, scoring=RMSE)
PCR_results2 = cross_val_score(PCR, X, y2, cv=kfold, scoring=RMSE)
```

#### Comparing ML models
In the following code, you can add many ML models to the comparison:
```python
models = []
models.append(('LR', LinearRegression()))
models.append(('XGB', xg.XGBRegressor()))
models.append(('MLP', MLPRegressor()))
```

## Conclusion
Please reach out to amine.boussetta@outlook.com for any feedback.
