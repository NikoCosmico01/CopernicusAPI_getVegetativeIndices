requireNDVI = True #B04, B08
requireNDMI = True #B08, B11
requireNDWI = True #B05, B06
requireMSAVI = True #B04, B08
requireEVI = True #B04, B08, B02

tifSize = [244, 244]

startDate = "2018-06-01" #from 00:00:00 midNight
endDate = "2018-09-30" #to 23:59:59

maxCloudCoverage = 15 #in %

dataFolder = "semiFinalSH"

#latLon = [latLowerLeftBBox, lonLowerLeftBBox, latUpperRightBBox, lonUpperRightBBox]

clientId = 'INSERT HERE'
clientSecret = 'INSERT HERE'

#False if using Sentinel Hub Processing API
usingDataspaceAPI = False

#Useful if reading bounding boxes coordinates from File
#File Line Structure: (fieldID, (latCentroid, lonCentroid), [latLowerLeftBBox, lonLowerLeftBBox, latUpperRightBBox, lonUpperRightBBox])
inputFile = "idFields.txt"