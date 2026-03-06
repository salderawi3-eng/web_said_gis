import io
import os
import zipfile
import tempfile
import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
st.set_page_config(page_title="GIS  saidgisweb", layout="wide")

st.markdown("""
<style>

/* خلفية الصفحة العامة */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #111827 40%, #0b1220 100%);
    color: #e5e7eb;
}

/* شريط جانبي */
section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(10px);
    border-right: 1px solid rgba(255,255,255,0.10);
    background: #1e293b !important;  /* لون أزرق داكن */

}
section[data-testid="stSidebar"] * {
    color: #e5e7eb !important;
}

/* عناوين */
h1, h2, h3, h4 {
    color: #f9fafb !important;
    letter-spacing: 0.2px;
}

/* بطاقات */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 16px;
    padding: 12px;
}

/* أزرار */
.stButton > button, .stDownloadButton > button {
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    color: #0b1220 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.55rem 1rem !important;
    font-weight: 700 !important;
}

/* Selectbox / input */
div[data-baseweb="select"] > div,
.stTextInput input,
.stMultiSelect div {
    background-color: rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #e5e7eb !important;
}

[data-testid="stFileUploaderDropzone"] {
    background-color: #334155 !important;
    border: 1px dashed #60a5fa !important;
    border-radius: 12px;
}

[data-testid="stFileUploaderDropzone"] * {
    color: #ffffff !important;
}

div[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.06) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
}

div[data-testid="stAlert"] {
    border-radius: 14px !important;
}

</style>
""", unsafe_allow_html=True)

st.title("Spatial & Attribute Join Web App")
st.write("Upload a Shapefile (ZIP) and a GeoJSON file to perform spatial or attribute joins and visualize the results on interactive maps.")

def read_geojson(uploaded_file) -> gpd.GeoDataFrame:
    try:
        content = uploaded_file.read()
        uploaded_file.seek(0)
        return gpd.read_file(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"GeoJSON Invalid GeoJSON file or unable to read it Details: {e}")

def read_shapefile_zip(uploaded_zip) -> gpd.GeoDataFrame:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "data.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())
            uploaded_zip.seek(0)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            shp_files = []
            for root, _, files in os.walk(tmpdir):
                for name in files:
                    if name.lower().endswith(".shp"):
                        shp_files.append(os.path.join(root, name))

            if not shp_files:
                raise ValueError("Invalid ZIP file. Please upload a valid Shapefile archive containing the required shp file")

            shp_path = shp_files[0]
            gdf = gpd.read_file(shp_path)
            return gdf

    except zipfile.BadZipFile:
        raise ValueError("The uploaded file is not a valid ZIP archive or it may be corrupted")
    except Exception as e:
        raise ValueError(f" Unable to read the Shapefile from the ZIP archive : {e}")

def make_map(gdf: gpd.GeoDataFrame, name: str):

    if gdf is None or gdf.empty:
        st.warning(f" No spatial data available for map display : {name}")
        return

    try:
        if gdf.crs is None:
            gdf_wgs = gdf
        else:
            gdf_wgs = gdf.to_crs(epsg=4326)
    except Exception:
        gdf_wgs = gdf

    center = [0, 0]
    try:
        c = gdf_wgs.geometry.unary_union.centroid
        center = [c.y, c.x]
    except Exception:
        pass

    m = folium.Map(location=center, zoom_start=6, control_scale=True)

    try:
        folium.GeoJson(
            data=gdf_wgs.__geo_interface__,
            name=name
        ).add_to(m)
        folium.LayerControl().add_to(m)
    except Exception as e:
        st.error(f"   error to display the map for  {name}. Details: {e}")
        return

    st_folium(m, height=320, width=None, key=f"map_{name}")

def preview_gdf(gdf: gpd.GeoDataFrame, n: int = 5):
    preview = gdf.head(n).copy()
    if "geometry" in preview.columns:
        preview["geometry"] = preview["geometry"].astype(str) 
    return preview

with st.sidebar:
    st.header("  File Upload ")

    left_zip = st.file_uploader(
        " Shapefile ZIP",
        type=["zip"],
        accept_multiple_files=False
    )

    right_geojson = st.file_uploader(
        " GeoJSON",
        type=["geojson", "json"],
        accept_multiple_files=False
    )


col_left, col_right = st.columns(2)

if "left_gdf" not in st.session_state:
    st.session_state.left_gdf = None
if "right_gdf" not in st.session_state:
    st.session_state.right_gdf = None
if "join_result" not in st.session_state:
    st.session_state.join_result = None
if "attr_result" not in st.session_state:
    st.session_state.attr_result = None

with col_left:
    st.subheader("  Shapefile ZIP")
    if left_zip is not None:
        with st.spinner("Reading the file..."):
            try:
                st.session_state.left_gdf = read_shapefile_zip(left_zip)
                st.success(" Left file uploaded successfully.")
            except ValueError as e:
                st.session_state.left_gdf = None
                st.error(str(e))

    if st.session_state.left_gdf is not None:
        make_map(st.session_state.left_gdf, "Left Layer")
        st.write("First 5 rows  :")
        st.dataframe(preview_gdf(st.session_state.left_gdf, 5))

with col_right:
    st.subheader(" GeoJSON")
    if right_geojson is not None:
        with st.spinner("Reading the file..."):
            try:
                st.session_state.right_gdf = read_geojson(right_geojson)
                st.success(" Right file uploaded successfully")
            except ValueError as e:
                st.session_state.right_gdf = None
                st.error(str(e))

    if st.session_state.right_gdf is not None:
        make_map(st.session_state.right_gdf, "Right Layer")
        st.write("First 5 rows:")
        st.dataframe(preview_gdf(st.session_state.right_gdf, 5))

st.divider()
st.header("Spatial Join ")

if st.session_state.left_gdf is None or st.session_state.right_gdf is None:
    st.warning("Upload the Left and Right files first, then perform the Spatial Join")
else:
    with st.sidebar:
        st.header(" إعدادات Spatial Join")

        spatial_pred = st.selectbox(
            "Select the spatial relationship  :",
            options=["intersects", "contains", "within"],
            index=0
        )

        how_option = st.selectbox(
            " Join type:",
            options=["left", "inner", "right"],
            index=0
        )

        run_spatial = st.button("Run")
    if run_spatial:
        with st.spinner(" Processing"):
            try:
                left_gdf = st.session_state.left_gdf
                right_gdf = st.session_state.right_gdf

                if left_gdf.crs is not None and right_gdf.crs is not None:
                    if left_gdf.crs != right_gdf.crs:
                        right_gdf = right_gdf.to_crs(left_gdf.crs)

                try:
                    result = gpd.sjoin(
                        left_gdf,
                        right_gdf,
                        how=how_option,
                        predicate=spatial_pred,
                    )
                except TypeError:
                    result = gpd.sjoin(
                        left_gdf,
                        right_gdf,
                        how=how_option,
                        op=spatial_pred,
                    )

                st.session_state.join_result = result

                if result.empty:
                    st.warning(" No results found: No spatial matches were detected")
                else:
                    st.success(f" Spatial Join completed successfully. Number of resulting records: {len(result)}")
                    st.subheader(" Results Preview (First 10 Rows)")
                    st.dataframe(preview_gdf(result, 10))

            except Exception as e:
                st.session_state.join_result = None
                st.error(f" error occurred during  Spatial Join: {e}")
st.divider()
st.header("Attribute Join ")

if st.session_state.left_gdf is None or st.session_state.right_gdf is None:
    st.warning("Upload both files first, then perform the Attribute Join")
else:
    left_cols = [c for c in st.session_state.left_gdf.columns if c != "geometry"]
    right_cols = [c for c in st.session_state.right_gdf.columns if c != "geometry"]

    if len(left_cols) == 0 or len(right_cols) == 0:
        st.error("There are not enough columns for Attribute Join (check the tables).")
    else:
        with st.sidebar:
            st.header("Attribute Join Settings")

            left_key = st.selectbox("Select join column from Left:", options=left_cols)
            right_key = st.selectbox("Select join column from Right:", options=right_cols)

            how_attr = st.selectbox(
                "Join type:",
                options=["left", "inner", "right", "outer"],
                index=0
            )

            run_attr = st.button(" Run Attribute Join")

        if run_attr:
            with st.spinner(" Processing Attribute Join"):
                try:
                    left_gdf = st.session_state.left_gdf.copy()
                    right_df = st.session_state.right_gdf.copy()

                    if "geometry" in right_df.columns:
                        right_df = right_df.drop(columns=["geometry"])

                    left_gdf[left_key] = left_gdf[left_key].astype(str)
                    right_df[right_key] = right_df[right_key].astype(str)

                    result_attr = left_gdf.merge(
                        right_df,
                        how=how_attr,
                        left_on=left_key,
                        right_on=right_key,
                        suffixes=("_L", "_R")
                    )

                    st.session_state.attr_result = result_attr

                    if result_attr.empty:
                        st.warning(" No results found: No attribute matches were detected")
                    else:
                        st.success(f" Attribute Join completed successfully. Number of resulting records: {len(result_attr)}")
                        st.subheader(" Results Preview (First 10 Rows)")
                        st.dataframe(preview_gdf(result_attr, 10))

                except Exception as e:
                    st.session_state.attr_result = None
                    st.error(f"  error occurred during Attribute Join Attribute Join: {e}")


st.divider()
st.header("  Download Result ")

final_result = None
final_name = None
if st.session_state.attr_result is not None:
    final_result = st.session_state.attr_result
    final_name = "attribute_join_result.geojson"
elif st.session_state.join_result is not None:
    final_result = st.session_state.join_result
    final_name = "spatial_join_result.geojson"

if final_result is None:
    st.info("Run Spatial Join or Attribute Join first to enable downloading.")
else:
    if final_result.empty:
        st.info("There is no file to download because the result is empty.")
    else:
        try:
            geojson_bytes = final_result.to_json().encode("utf-8")
            st.download_button(
                label="Download GeoJSON Result",
                data=geojson_bytes,
                file_name=final_name,
                mime="application/geo+json"
            )
        except Exception as e:
            st.error(f"Failed to prepare GeoJSON file for download: {e}")
