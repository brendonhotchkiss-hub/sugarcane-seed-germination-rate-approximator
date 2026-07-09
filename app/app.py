import streamlit as st
import pandas as pd
import tempfile
import os
from pathlib import Path
from datetime import datetime

from germination_pipeline import load_model, analyze_image

st.set_page_config(
    page_title="Sugarcane Germination Analyzer",
    page_icon="🌱",
    layout="wide"
)

@st.cache_resource
def get_model():
    try:
        return load_model()
    except FileNotFoundError as e:
        st.error(f"Model not found: {e}")
        st.stop()

st.title("🌱 Sugarcane Germination Analyzer")
st.markdown(
    "Upload one or more petri dish images to estimate total seed count, "
    "germinated seed count, and germination rate."
)
st.divider()

uploaded_files = st.file_uploader(
    "Select image(s)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    svm, scaler = get_model()

    uploaded_names = [f.name for f in uploaded_files]
    if "last_uploaded" not in st.session_state or \
       st.session_state.last_uploaded != uploaded_names:

        results = []
        progress = st.progress(0, text="Analyzing images...")

        for i, uploaded_file in enumerate(uploaded_files):
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            try:
                result = analyze_image(
                    tmp_path,
                    original_filename=uploaded_file.name,
                    svm=svm,
                    scaler=scaler
                )
                results.append(result)
            except Exception as e:
                st.warning(f"Could not process {uploaded_file.name}: {e}")
            finally:
                os.unlink(tmp_path)

            progress.progress(
                (i + 1) / len(uploaded_files),
                text=f"Analyzing {uploaded_file.name}..."
            )

        progress.empty()
        st.session_state.results       = results
        st.session_state.last_uploaded = uploaded_names
        st.session_state.selected_img  = results[0]["image_name"] if results else None

    results = st.session_state.get("results", [])

    if results:
        st.subheader("Results")

        df = pd.DataFrame([{
            "Petri ID"             : r["petri_id"],
            "Image"                : r["image_name"],
            "Total Seeds"          : r["total_seeds"],
            "Germinated Seeds"     : r["germinated_seeds"],
            "Germination Rate (%)": r["germination_rate"],
        } for r in results])

        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(results) > 1:
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Images Analyzed", len(results))
            col2.metric("Avg Germination Rate",
                        f"{df['Germination Rate (%)'].mean():.1f}%")
            col3.metric("Rate Range",
                        f"{df['Germination Rate (%)'].min():.1f}% – "
                        f"{df['Germination Rate (%)'].max():.1f}%")

        st.divider()
        st.subheader("Annotated Image")
        st.caption(
            "🟠 Orange — single seed  |  "
            "🔴 Red ~N — cluster of N estimated seeds  |  "
            "🟢 Green — germination detected  |  "
            "🔴+🟢 overlap — germination detected within a cluster (individual count unknown)"
        )

        image_names = [r["image_name"] for r in results]
        selected = st.selectbox(
            "Select image to view:",
            options=image_names,
            index=image_names.index(st.session_state.selected_img)
            if st.session_state.get("selected_img") in image_names else 0,
            key="selected_img"
        )

        selected_result = next(r for r in results if r["image_name"] == selected)
        caption = (
            f"Petri ID: {selected_result['petri_id']}  |  "
            f"{selected_result['image_name']} — "
            f"Total: {selected_result['total_seeds']}  |  "
            f"Germinated: {selected_result['germinated_seeds']}  |  "
            f"Rate: {selected_result['germination_rate']}%"
        )

        st.image(selected_result["annotated_img"], caption=caption, width=600)

        with st.expander("🔍 Expand for full resolution inspection"):
            st.image(
                selected_result["annotated_img"],
                caption=caption,
                use_container_width=True
            )

        st.divider()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download results as CSV",
            data=csv,
            file_name=f"germination_results_{timestamp}.csv",
            mime="text/csv"
        )

st.divider()
st.caption(
    "Sugarcane Germination Analyzer — UTA / USDA ARS  |  "
    "Model: SVM + Contour counting  |  "
    "For research use"
)
