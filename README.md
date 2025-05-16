This repository contains a Python script designed to interact with the Copernicus Dataspace API  or Sentinel Hub Processing API to obtain field-level vegetation indices such as NDVI, NDMI, NDWI, MSAVI and AVI from Sentinel-2 L2A imagery.
The script can allow you to download fields indeces reading from a .txt file that contains a list of Bounding Boxes (both lat and lon of lower-left and upper-right vertices) or directly inserting [latLowerLeftBBox, lonLowerLeftBBox, latUpperRightBBox, lonUpperRightBBox]. The API response has to be initially saved in order to mantain the CSR of the downloaded .tif file, the response will then be elaborated to group all the same-day downloaded indeces under a common folder and each index will be inserted in a specified file (es <file>_ndvi.tig ecc.).
If you do NOT want to read the Bounding Boxes from file you will need to edit the script a little bit. 

The script 'pippalineaCopernicus.py' is intended for single-thread usage while the 'pippalineaParallelized.py' is intended to run with multiple threads to maximize time efficiency. If you need to download only few plots you can use the single-thread one.

All the script configuration is inside 'config.py' File. To retrieve clientId and clientSecret you nees to Sign-Up to [Dataspace Copernicus Dashboard](https://shapps.dataspace.copernicus.eu/dashboard/#/) then go to ***User settings*** and create a ***OAuth client*** key.

##Linux Usage
After cloning the Repo I suggest creating a Python Virtual Environment:
'''
python -m venv venv
source venv/bin/activate
'''
Install required packages inside Env:
'''
pip install rasterio sentinelhub
'''
Run either the single-thread or the multi-thread version.

You can put the running script in background using 'screen' or other tools so you can close the terminal without interrupting the job.