import streamlit as st
import geemap.foliumap as geemap
import ee
import datetime

# Authenticate and initialize the Earth Engine library.
service_account = st.secrets["google"]["service_account"]
private_key = st.secrets["google"]["private_key"]

credentials = ee.ServiceAccountCredentials(service_account, private_key)
ee.Initialize(credentials)

# Function to calculate NDVI for each image in the collection.
def calculate_ndvi(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return image.addBands(ndvi)

# Function to update the map based on selected AOI and dates
def update_map(aoi, start_date, end_date, show_ndvi, opacity):
    if not isinstance(aoi, ee.Geometry):
        try:
            aoi = ee.Geometry.Polygon(aoi['coordinates'])
        except Exception as e:
            st.error("Invalid AOI. Please draw a valid area of interest (AOI) on the map.")
            return None
    
    sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR') \
                    .filterBounds(aoi) \
                    .filterDate(start_date, end_date) \
                    .map(calculate_ndvi)
    
    ndvi_collection = sentinel2.select('NDVI')
    ndvi_median = ndvi_collection.median()
    
    timestamps = ndvi_collection.aggregate_array('system:time_start').getInfo()
    dates = [datetime.datetime.utcfromtimestamp(ts / 1000).strftime('%Y-%m-%d') for ts in timestamps]
    st.write("Timestamps of the images contributing to the median NDVI:", dates)
    
    spatial_resolution = sentinel2.first().select('B8').projection().nominalScale().getInfo()
    st.write(f"Spatial resolution of the NDVI: {spatial_resolution} meters")
    
    ndvi_vis_params = {
        'min': -1,
        'max': 1,
        'palette': ['red', 'orange', 'yellow', 'green', 'darkgreen'],
        'opacity': opacity
    }
    
    if show_ndvi:
        return ndvi_median.visualize(**ndvi_vis_params)
    else:
        return None

# Streamlit interface
st.title("NDVI Map Viewer")
start_date = st.date_input("Start Date", datetime.date(2023, 1, 1))
end_date = st.date_input("End Date", datetime.date.today())
show_ndvi = st.checkbox("Show NDVI", value=True)
opacity = st.slider("Opacity", 0.0, 1.0, 1.0, 0.1)

Map = geemap.Map(draw_export=True, basemap='HYBRID')
Map.add_draw_control()
Map.centerObject(ee.Geometry.Point([-75.8374400075242, 38.610915354251574]), 15)

if st.button("Update Map"):
    aoi = Map.user_roi
    ndvi_layer = update_map(aoi, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'), show_ndvi, opacity)
    if ndvi_layer:
        Map.addLayer(ndvi_layer, {}, 'Median NDVI')

Map.to_streamlit(height=700)
