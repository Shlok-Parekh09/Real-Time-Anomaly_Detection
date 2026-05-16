"""
K-Nearest: Real-Time Anomaly & Forgery Detection
A real-time digital forensics engine using K-Nearest Neighbors (KNN) algorithm
to detect forged or tampered financial/land documents.

Author: Lead ML Engineer
Purpose: Hackathon Prototype Demo
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="K-Nearest: Document Forgery Detection",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS FOR PROFESSIONAL STYLING
# ============================================================================

st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 3px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-banner {
        padding: 1.5rem;
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-banner {
        padding: 1.5rem;
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA GENERATION & MODEL INITIALIZATION
# ============================================================================

@st.cache_resource
def generate_authentic_dataset(n_samples=200, random_state=42):
    """
    Generate synthetic dataset of authentic documents.
    Creates a tight cluster representing legitimate documents.

    Args:
        n_samples: Number of authentic documents to generate
        random_state: Random seed for reproducibility

    Returns:
        numpy.ndarray: Array of shape (n_samples, 3) with feature values
    """
    np.random.seed(random_state)

    # Feature 1: Metadata Consistency Score (mean: 75, std: 8)
    metadata_scores = np.random.normal(loc=75, scale=8, size=n_samples)

    # Feature 2: Layout & Structural Integrity (mean: 80, std: 7)
    layout_scores = np.random.normal(loc=80, scale=7, size=n_samples)

    # Feature 3: Font & Pixel Variance (mean: 70, std: 9)
    font_scores = np.random.normal(loc=70, scale=9, size=n_samples)

    # Clip values to ensure they're within 0-100 range
    authentic_data = np.column_stack([
        np.clip(metadata_scores, 0, 100),
        np.clip(layout_scores, 0, 100),
        np.clip(font_scores, 0, 100)
    ])

    return authentic_data


@st.cache_resource
def train_knn_model(authentic_data, n_neighbors=5):
    """
    Train KNN model on authentic document dataset.

    Args:
        authentic_data: numpy array of authentic document features
        n_neighbors: Number of nearest neighbors to consider

    Returns:
        tuple: (trained KNN model, fitted scaler)
    """
    # Standardize features for better distance calculation
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(authentic_data)

    # Initialize and fit KNN model
    knn_model = NearestNeighbors(n_neighbors=n_neighbors, metric='euclidean')
    knn_model.fit(scaled_data)

    return knn_model, scaler


def calculate_anomaly_score(uploaded_features, knn_model, scaler, authentic_data_scaled):
    """
    Calculate anomaly score for uploaded document.

    Args:
        uploaded_features: numpy array of uploaded document features
        knn_model: Trained KNN model
        scaler: Fitted StandardScaler
        authentic_data_scaled: Scaled authentic data for threshold calculation

    Returns:
        tuple: (average_distance, threshold_95, is_anomaly)
    """
    # Scale the uploaded document features
    uploaded_scaled = scaler.transform(uploaded_features.reshape(1, -1))

    # Find k-nearest neighbors and calculate distances
    distances, indices = knn_model.kneighbors(uploaded_scaled)
    avg_distance = np.mean(distances)

    # Calculate dynamic threshold (95th percentile of authentic cluster)
    all_distances, _ = knn_model.kneighbors(authentic_data_scaled)
    threshold_95 = np.percentile(np.mean(all_distances, axis=1), 95)

    # Determine if document is anomalous
    is_anomaly = avg_distance > threshold_95

    return avg_distance, threshold_95, is_anomaly


def generate_insights(uploaded_features, authentic_data, is_anomaly):
    """
    Generate intelligent insights based on feature deviations.

    Args:
        uploaded_features: numpy array of uploaded document features
        authentic_data: numpy array of authentic document features
        is_anomaly: boolean indicating if document is anomalous

    Returns:
        str: Detailed insight message
    """
    if not is_anomaly:
        return "✅ All document features align with authentic baseline patterns."

    # Calculate mean and std of authentic documents for each feature
    feature_names = ["Metadata Consistency", "Layout & Structural Integrity", "Font & Pixel Variance"]
    authentic_means = np.mean(authentic_data, axis=0)
    authentic_stds = np.std(authentic_data, axis=0)

    # Identify features that deviate significantly (>2 standard deviations)
    deviations = []
    for i, (feature_val, mean, std, name) in enumerate(
        zip(uploaded_features, authentic_means, authentic_stds, feature_names)
    ):
        z_score = abs((feature_val - mean) / std)
        if z_score > 2:
            direction = "abnormally high" if feature_val > mean else "abnormally low"
            deviations.append(f"{name} ({direction}: {z_score:.2f}σ)")

    if deviations:
        return f"🚨 Flagged: Significant deviation detected in: {', '.join(deviations)}"
    else:
        return "⚠️ Flagged: Overall pattern does not match authentic document cluster."


# ============================================================================
# INITIALIZE DATA AND MODEL
# ============================================================================

# Generate authentic dataset
authentic_data = generate_authentic_dataset(n_samples=200)

# Train KNN model
knn_model, scaler = train_knn_model(authentic_data, n_neighbors=5)

# Scale authentic data for visualization and threshold calculation
authentic_data_scaled = scaler.transform(authentic_data)

# ============================================================================
# STREAMLIT UI - HEADER
# ============================================================================

st.markdown('<div class="main-header">🔍 K-Nearest: Real-Time Anomaly & Forgery Detection</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Powered Digital Forensics Engine for Financial & Land Documents</div>',
            unsafe_allow_html=True)

# ============================================================================
# STREAMLIT UI - SIDEBAR (INPUT CONTROLS)
# ============================================================================

st.sidebar.header("📄 Document Upload & Analysis")

# Simulated upload button
st.sidebar.info("**Simulation Mode:** Adjust sliders below to simulate document feature extraction.")

uploaded_file = st.sidebar.button("🔼 Simulate Document Upload", type="primary", use_container_width=True)

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ Feature Adjustments")
st.sidebar.caption("Modify extracted features to simulate different document scenarios")

# Feature sliders
metadata_score = st.sidebar.slider(
    "📊 Metadata Consistency Score",
    min_value=0,
    max_value=100,
    value=75,
    help="Consistency of document metadata (timestamps, author info, etc.)"
)

layout_score = st.sidebar.slider(
    "📐 Layout & Structural Integrity",
    min_value=0,
    max_value=100,
    value=80,
    help="Alignment, margins, and structural consistency"
)

font_score = st.sidebar.slider(
    "🔤 Font & Pixel Variance",
    min_value=0,
    max_value=100,
    value=70,
    help="Font consistency and pixel-level analysis"
)

st.sidebar.markdown("---")
st.sidebar.info("""
**ℹ️ How it works:**
- Green dots: 200 authentic documents
- Large dot: Your uploaded document
- Distance measures similarity to authentic cluster
- Higher distance = Higher anomaly risk
""")

# ============================================================================
# MAIN DASHBOARD - ANALYSIS & VISUALIZATION
# ============================================================================

# Create uploaded document feature vector
uploaded_features = np.array([metadata_score, layout_score, font_score])

# Calculate anomaly score
avg_distance, threshold_95, is_anomaly = calculate_anomaly_score(
    uploaded_features, knn_model, scaler, authentic_data_scaled
)

# Generate insights
insight_message = generate_insights(uploaded_features, authentic_data, is_anomaly)

# ============================================================================
# METRIC CARDS
# ============================================================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📏 Distance from Baseline",
        value=f"{avg_distance:.4f}",
        delta=f"{avg_distance - threshold_95:.4f}" if is_anomaly else None,
        delta_color="inverse"
    )

with col2:
    st.metric(
        label="🎯 Detection Threshold",
        value=f"{threshold_95:.4f}",
        help="95th percentile of authentic cluster distances"
    )

with col3:
    st.metric(
        label="📋 Authentic Documents",
        value="200",
        help="Size of training dataset"
    )

with col4:
    status_emoji = "🚨" if is_anomaly else "✅"
    status_text = "ANOMALY" if is_anomaly else "AUTHENTIC"
    st.metric(
        label="🔍 Classification",
        value=f"{status_emoji} {status_text}"
    )

st.markdown("---")

# ============================================================================
# VERIFICATION BANNER
# ============================================================================

if is_anomaly:
    st.markdown(f"""
    <div class="warning-banner">
        <h2 style="color: #dc3545; margin: 0;">⚠️ ANOMALY DETECTED</h2>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            <strong>Status:</strong> Document flagged as potentially forged or tampered<br>
            <strong>Risk Level:</strong> HIGH (Distance exceeds 95th percentile threshold)<br>
            <strong>Recommendation:</strong> Requires manual forensic review
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="success-banner">
        <h2 style="color: #28a745; margin: 0;">✅ DOCUMENT VERIFIED: AUTHENTIC</h2>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            <strong>Status:</strong> Document matches authentic baseline patterns<br>
            <strong>Confidence:</strong> HIGH (Within expected variance range)<br>
            <strong>Action:</strong> Cleared for processing
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# INTELLIGENT INSIGHTS PANEL
# ============================================================================

st.subheader("🧠 AI-Generated Forensic Insights")

insight_col1, insight_col2 = st.columns([2, 1])

with insight_col1:
    if is_anomaly:
        st.error(insight_message)
    else:
        st.success(insight_message)

with insight_col2:
    st.metric(
        label="Anomaly Confidence",
        value=f"{min(100, (avg_distance / threshold_95) * 100):.1f}%",
        help="Percentage relative to detection threshold"
    )

# ============================================================================
# 3D INTERACTIVE VISUALIZATION
# ============================================================================

st.markdown("---")
st.subheader("📊 3D Feature Space Visualization")

# Scale uploaded features for plotting
uploaded_scaled = scaler.transform(uploaded_features.reshape(1, -1))

# Create 3D scatter plot
fig = go.Figure()

# Plot authentic documents (green cluster)
fig.add_trace(go.Scatter3d(
    x=authentic_data_scaled[:, 0],
    y=authentic_data_scaled[:, 1],
    z=authentic_data_scaled[:, 2],
    mode='markers',
    name='Authentic Documents',
    marker=dict(
        size=4,
        color='#28a745',
        opacity=0.6,
        symbol='circle'
    ),
    hovertemplate='<b>Authentic Document</b><br>' +
                  'Metadata: %{x:.2f}<br>' +
                  'Layout: %{y:.2f}<br>' +
                  'Font: %{z:.2f}<br>' +
                  '<extra></extra>'
))

# Plot uploaded document (red if anomaly, blue if authentic)
uploaded_color = '#dc3545' if is_anomaly else '#007bff'
uploaded_label = 'Uploaded (ANOMALY)' if is_anomaly else 'Uploaded (AUTHENTIC)'

fig.add_trace(go.Scatter3d(
    x=[uploaded_scaled[0, 0]],
    y=[uploaded_scaled[0, 1]],
    z=[uploaded_scaled[0, 2]],
    mode='markers',
    name=uploaded_label,
    marker=dict(
        size=15,
        color=uploaded_color,
        symbol='diamond',
        line=dict(color='white', width=2)
    ),
    hovertemplate='<b>Uploaded Document</b><br>' +
                  'Metadata: %{x:.2f}<br>' +
                  'Layout: %{y:.2f}<br>' +
                  'Font: %{z:.2f}<br>' +
                  f'Distance: {avg_distance:.4f}<br>' +
                  '<extra></extra>'
))

# Update layout
fig.update_layout(
    scene=dict(
        xaxis_title='Metadata Consistency (Scaled)',
        yaxis_title='Layout Integrity (Scaled)',
        zaxis_title='Font Variance (Scaled)',
        camera=dict(
            eye=dict(x=1.5, y=1.5, z=1.3)
        ),
        bgcolor='rgba(240, 240, 240, 0.9)'
    ),
    showlegend=True,
    legend=dict(
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor='rgba(255, 255, 255, 0.8)'
    ),
    height=600,
    margin=dict(l=0, r=0, b=0, t=30),
    hovermode='closest'
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# FEATURE BREAKDOWN TABLE
# ============================================================================

st.markdown("---")
st.subheader("📈 Detailed Feature Analysis")

# Calculate statistics
feature_comparison = pd.DataFrame({
    'Feature': ['Metadata Consistency', 'Layout & Structural Integrity', 'Font & Pixel Variance'],
    'Uploaded Value': uploaded_features,
    'Authentic Mean': np.mean(authentic_data, axis=0),
    'Authentic Std Dev': np.std(authentic_data, axis=0),
    'Z-Score': [(uploaded_features[i] - np.mean(authentic_data[:, i])) / np.std(authentic_data[:, i])
                for i in range(3)]
})

# Add status column
feature_comparison['Status'] = feature_comparison['Z-Score'].apply(
    lambda x: '🚨 Anomalous' if abs(x) > 2 else '✅ Normal'
)

# Format numerical columns
feature_comparison['Uploaded Value'] = feature_comparison['Uploaded Value'].map('{:.2f}'.format)
feature_comparison['Authentic Mean'] = feature_comparison['Authentic Mean'].map('{:.2f}'.format)
feature_comparison['Authentic Std Dev'] = feature_comparison['Authentic Std Dev'].map('{:.2f}'.format)
feature_comparison['Z-Score'] = feature_comparison['Z-Score'].map('{:.2f}'.format)

st.dataframe(
    feature_comparison,
    use_container_width=True,
    hide_index=True
)

# ============================================================================
# FOOTER & TECHNICAL DETAILS
# ============================================================================

st.markdown("---")
with st.expander("🔧 Technical Details & Methodology"):
    st.markdown("""
    ### Algorithm: K-Nearest Neighbors (KNN) for Anomaly Detection

    **Training Phase:**
    - Dataset: 200 synthetically generated authentic documents
    - Features: 3 engineered metrics (Metadata, Layout, Font) normalized using StandardScaler
    - Model: Unsupervised KNN with k=5 neighbors

    **Detection Phase:**
    1. Calculate Euclidean distance to k-nearest neighbors in authentic cluster
    2. Compare average distance against dynamic threshold (95th percentile)
    3. Documents exceeding threshold flagged as anomalies

    **Feature Engineering:**
    - **Metadata Consistency:** Analyzes timestamp coherence, author patterns, edit history
    - **Layout Integrity:** Evaluates margins, alignment, structural patterns
    - **Font Variance:** Pixel-level font analysis, kerning, rendering artifacts

    **Advantages:**
    - ✅ No labeled forgery data required (unsupervised learning)
    - ✅ Real-time detection with minimal latency
    - ✅ Interpretable results with feature-level insights
    - ✅ Adaptive to new document types

    **Use Cases:**
    - Financial document verification (invoices, receipts, contracts)
    - Land registry deed authentication
    - Legal document tampering detection
    - Insurance claim fraud prevention
    """)

st.markdown("---")
st.caption("🏆 K-Nearest: Real-Time Anomaly Detection Engine | Built for Hackathon Prototype | Powered by Python, Streamlit & scikit-learn")
