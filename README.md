# 🔍 K-Nearest: Real-Time Anomaly & Forgery Detection

> AI-Powered Digital Forensics Engine for Financial & Land Documents

## Overview

K-Nearest is a real-time digital forensics prototype that leverages the K-Nearest Neighbors (KNN) algorithm to detect forged or tampered financial and land documents by identifying them as statistical outliers from an authentic baseline cluster.

## Features

✅ **Unsupervised Anomaly Detection** - No labeled forgery data required  
✅ **Real-Time Analysis** - Instant detection with interactive visualization  
✅ **3D Feature Space Visualization** - Interactive Plotly charts for intuitive understanding  
✅ **Intelligent Insights** - AI-generated explanations pinpointing exact deviations  
✅ **Dynamic Thresholds** - Adaptive 95th percentile-based anomaly scoring  
✅ **Professional UI** - Clean, judge-ready Streamlit interface

## Technical Architecture

### ML Pipeline

1. **Data Generation**: 200 synthetic authentic documents with 3 engineered features
2. **Feature Engineering**: 
   - Metadata Consistency Score (0-100)
   - Layout & Structural Integrity (0-100)
   - Font & Pixel Variance (0-100)
3. **Model**: Unsupervised KNN (k=5) with StandardScaler normalization
4. **Detection**: Euclidean distance-based outlier detection with dynamic threshold

### Tech Stack

- **Framework**: Streamlit
- **ML Library**: scikit-learn
- **Visualization**: Plotly (3D interactive charts)
- **Data Processing**: NumPy, Pandas
- **Language**: Python 3.8+

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Clone or navigate to the project directory**

```bash
cd /path/to/k-nearest-forgery-detection
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

## Running the Application

### Start the Streamlit server

```bash
streamlit run app.py
```

The application will automatically open in your default browser at `http://localhost:8501`

### Alternative: Specify port

```bash
streamlit run app.py --server.port 8080
```

## Usage Guide

### 1. Document Upload Simulation

Click the **"🔼 Simulate Document Upload"** button in the sidebar to initialize the analysis mode.

### 2. Feature Adjustment

Use the three sliders to simulate different document scenarios:

- **📊 Metadata Consistency Score**: Adjust to simulate metadata tampering
- **📐 Layout & Structural Integrity**: Modify to test structural anomalies  
- **🔤 Font & Pixel Variance**: Change to simulate font manipulation

### 3. Real-Time Analysis

Watch the dashboard update in real-time:

- **Metric Cards**: Distance from baseline, threshold, classification status
- **Verification Banner**: Green (Authentic) or Red (Anomaly) alert
- **AI Insights**: Detailed explanation of detected anomalies
- **3D Visualization**: Interactive scatter plot showing document positioning

### 4. Interpret Results

- **Green Success Banner**: Document verified as authentic
- **Red Warning Banner**: Anomaly detected with specific insights
- **Feature Analysis Table**: Detailed Z-score breakdown per feature

## Demo Scenarios

### Scenario 1: Authentic Document (Default)
- Metadata: 75, Layout: 80, Font: 70
- **Result**: ✅ AUTHENTIC

### Scenario 2: Metadata Tampering
- Metadata: 30, Layout: 80, Font: 70
- **Result**: 🚨 ANOMALY - Flagged for abnormal metadata

### Scenario 3: Complete Forgery
- Metadata: 20, Layout: 40, Font: 95
- **Result**: 🚨 ANOMALY - Multiple deviations detected

## File Structure

```
k-nearest-forgery-detection/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Algorithm Details

### K-Nearest Neighbors (KNN) for Anomaly Detection

**Why KNN?**
- No labeled forgery examples needed (unsupervised)
- Naturally detects outliers based on distance metrics
- Computationally efficient for real-time analysis
- Interpretable results

**Detection Logic:**
1. Fit KNN model on authentic document cluster
2. Calculate average distance to k=5 nearest neighbors for new document
3. Compare against 95th percentile threshold of authentic cluster
4. Flag as anomaly if distance exceeds threshold

**Feature Scaling:**
- StandardScaler normalization ensures equal feature weight
- Prevents dominant features from skewing distance calculations

## Performance Characteristics

- **Dataset Size**: 200 authentic documents (expandable)
- **Inference Time**: < 50ms per document
- **False Positive Rate**: ~5% (by design of 95th percentile threshold)
- **Scalability**: Linear with dataset size O(n)

## Hackathon Presentation Tips

1. **Start with Default**: Show authentic document verification (green banner)
2. **Demonstrate Tampering**: Gradually adjust sliders to show anomaly detection
3. **Highlight 3D Viz**: Rotate the plot to show cluster separation
4. **Explain Insights**: Point out the AI-generated forensic insights
5. **Technical Deep-Dive**: Use the expandable "Technical Details" section

## Future Enhancements

- [ ] Upload real PDF/image documents with OCR feature extraction
- [ ] Ensemble methods (KNN + Isolation Forest + One-Class SVM)
- [ ] Explainable AI (SHAP values for feature importance)
- [ ] Historical audit log and batch processing
- [ ] API endpoint for integration with document management systems
- [ ] Deep learning-based feature extraction from raw document images

## License

This is a hackathon prototype for educational and demonstration purposes.

## Contact

Built by: Lead ML Engineer  
Purpose: Hackathon Prototype Demo  
Tech: Python | Streamlit | scikit-learn | Plotly

---

**🏆 Ready for Judges!** Clean code, professional UI, real-time interactivity.
