import shutil
from sentinelhub import SentinelHubRequest, DataCollection, MimeType, CRS, BBox, SHConfig, Geometry # type: ignore
import rasterio
import datetime as dt
import config as confFile # type: ignore
import os
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

# Credentials
config = SHConfig()
config.sh_client_id = confFile.clientId
config.sh_client_secret = confFile.clientSecret
if (confFile.usingDataspaceAPI):
    config.sh_token_url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    config.sh_base_url = "https://sh.dataspace.copernicus.eu"

requiredBands = []
indicesCodeBlocks = []
concatParts = []
listDeclaration = []
indicesNumber = 0

def addBand(band):
    if band not in requiredBands:
        requiredBands.append(band)

if confFile.requireNDVI:
    addBand("B04")
    addBand("B08")
    indicesNumber+=1
    listDeclaration.append("let ndvi = new Array(n_observations).fill(0)")
    indicesCodeBlocks.append('ndvi[index] = (sample.B08 - sample.B04) / (sample.B08 + sample.B04);')
    concatParts.append('ndvi')

if confFile.requireNDMI:
    addBand("B08")
    addBand("B11")
    indicesNumber+=1
    listDeclaration.append("let ndmi = new Array(n_observations).fill(0)")
    indicesCodeBlocks.append('ndmi[index] = (sample.B08 - sample.B11) / (sample.B08 + sample.B11);')
    concatParts.append('ndmi')

if confFile.requireNDWI:
    addBand("B03")
    addBand("B08")
    indicesNumber+=1
    listDeclaration.append("let ndwi = new Array(n_observations).fill(0)")
    indicesCodeBlocks.append('ndwi[index] = (sample.B03 - sample.B08) / (sample.B03 + sample.B08);')
    concatParts.append('ndwi')

if confFile.requireMSAVI:
    addBand("B04")
    addBand("B08")
    indicesNumber+=1
    listDeclaration.append("let msavi = new Array(n_observations).fill(0)")
    indicesCodeBlocks.append('msavi[index] = (2 * sample.B08 + 1 - Math.sqrt((2 * sample.B08 + 1) ** 2 - 8 * (sample.B08 - sample.B04))) / 2;')
    concatParts.append('msavi')

if confFile.requireEVI == True:
    print(confFile.requireEVI)
    addBand("B04")
    addBand("B08")
    addBand("B02")
    indicesNumber+=1
    listDeclaration.append("let evi = new Array(n_observations).fill(0)")
    indicesCodeBlocks.append('evi[index] = 2.5 * (sample.B08 - sample.B04) / (sample.B08 + 6 * sample.B04 - 7.5 * sample.B02 + 1);')
    concatParts.append('evi')

indexFinalBlock = "\n      ".join(indicesCodeBlocks)
listDeclarationFinal = "\n      ".join(listDeclaration)

if indicesNumber == 0:
    print("At least one index is required to be TRUE")
    exit()
    
print("Formule:\n", indexFinalBlock)
print("Required Bands:", requiredBands)

idList = []
bboxList = []

try:
    with open(confFile.inputFile) as file:
        for line in file:
            line = line.strip()
            if line :
                entry = eval(line) #Genero Tupla
                if os.path.exists(os.path.join(confFile.startDate[:4], f"Field{entry[0]}")):
                    print(f'fieldId {entry[0]} Already Present - Skipping')
                else:
                    idList.append(entry[0])
                    bboxList.append(entry[2])
except FileNotFoundError:
    print("File idFieldsPoint NOT Found")
    exit(0)

#Inizio Eval
evalscript = f"""
function setup() {{
    return {{
      input: [{{
        bands: {requiredBands},
        units: "DN"
      }}],
      output: {{
        bands: 1,
        sampleType: SampleType.FLOAT32
      }},
      mosaicking: Mosaicking.ORBIT
    }}
  }}
  
  function updateOutput(outputs, collection) {{
      Object.values(outputs).forEach((output) => {{
          output.bands = collection.scenes.length*{indicesNumber};
      }});
  }}

  function updateOutputMetadata(scenes, inputMetadata, outputMetadata) {{
      var dds = [];
      for (i=0; i<scenes.length; i++){{
        dds.push(scenes[i].date)
      }}
      outputMetadata.userData = {{ "acquisition_dates":  JSON.stringify(dds) }}
  }}
  
  function evaluatePixel(samples) {{
    var n_observations = samples.length;
        
    {listDeclarationFinal}
    
    // Fill the array with NDVI values
    samples.forEach((sample, index) => {{
      {indexFinalBlock}
    }});

    let jointIndex = {concatParts[0]};
    {' '.join([f'jointIndex = jointIndex.concat({name});' for name in concatParts[1:]])};

    return jointIndex;

  }}
"""
#print(evalscript)

def divideList(lst, n):
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]

def processChunk(threadId, bboxes, idList, config, evalscript, confFile, concatParts, indicesNumber):
    progressLock = Lock()
    completedTasks = 0
    totalTasks = len(bboxList)

    if (confFile.usingDataspaceAPI):
        myDataCollection = DataCollection.SENTINEL2_L2A.define_from(name="s2l2a", service_url="https://sh.dataspace.copernicus.eu")
    else:
        myDataCollection = DataCollection.SENTINEL2_L2A

    for localIndex, bboxValue in enumerate(bboxes):
        globalIndex = (threadId * len(bboxes)) + localIndex

        folder = f"{confFile.dataFolder}_{threadId}_{localIndex}"

        bbox = BBox(bbox=bboxValue, crs=CRS.WGS84)

        #Use only if Not reading from File
        #bbox = BBox(bbox=confFile.latLon, crs=CRS.WGS84)

        request = SentinelHubRequest(
            data_folder=folder,
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=myDataCollection,     
                    time_interval=(confFile.startDate, confFile.endDate),
                    other_args={"dataFilter": {"mosaickingOrder": "leastCC", "maxCloudCoverage": confFile.maxCloudCoverage}},
                ),
            ],
            responses=[
                SentinelHubRequest.output_response('default', MimeType.TIFF),
                SentinelHubRequest.output_response('userdata', MimeType.JSON),
            ],
            bbox=bbox,
            size=confFile.tifSize,
            config=config
        )

        start = time.time()

        #Saving is needed to mantain CRS Data
        response = request.get_data(save_data=True)

        end = time.time()

        for root, dirs, files in os.walk(folder):
            for file in files:
                if file == 'response.tar':
                    tarFilePath = os.path.join(root, file)

                    with tarfile.open(tarFilePath, "r") as tar:
                        tar.extractall(path=folder)
                    break


        image_path = os.path.join(folder, 'default.tif')
        image = rasterio.open(image_path, mode="r")

        dates = response[0]['userdata.json']['acquisition_dates']
        finalData = dates.replace("\"", "").replace("[", "").replace("]", "").split(",")

        startBand = 1
        for i, date in enumerate(finalData):
            outputDir = os.path.join(date[0:4], f"Field{idList[globalIndex]}", date[0:10])
            os.makedirs(outputDir, exist_ok=True)

            for j in range(indicesNumber):
                fileName = f"Field{idList[globalIndex]}_{date[0:10]}_{concatParts[j]}.tif"
                filepath = os.path.join(outputDir, fileName)
                bandData = image.read(startBand + j)

                with rasterio.open(filepath, 'w', **{**image.profile, "count": 1}) as dst:
                    dst.write(bandData, 1)

            startBand += indicesNumber

        image.close()
        shutil.rmtree(folder)
        print(f"[Thread {threadId}] Field {idList[globalIndex]} Ended in {end - start:.2f}s")

        with progressLock:
            completedTasks += 1
            percent = (completedTasks / totalTasks) * 100
            print(f"[Progress] {completedTasks}/{totalTasks} ({percent:.2f}%) complete")

numThreads = 3  # Use 3 or 4 MAX to avoid hitting Server Rate Limit
bboxChunks = divideList(bboxList, numThreads)

with ThreadPoolExecutor(max_workers=numThreads) as executor:
    futures = [
        executor.submit(
            processChunk, threadId, bboxChunk, idList, config, evalscript, confFile, concatParts, indicesNumber
        )
        for threadId, bboxChunk in enumerate(bboxChunks)
    ]
    for future in futures:
        future.result()