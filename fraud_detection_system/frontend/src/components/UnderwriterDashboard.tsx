import React, { useState } from 'react';
import { Upload, AlertTriangle, CheckCircle, Search, ShieldAlert, FileText, Settings, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

interface AnalysisResult {
  file_name: string;
  risk_score: number;
  heatmap_image_b64: string;
  anomalies: string[];
  metadata: Record<string, string>;
  extracted_text: string;
  validation_status: string;
  validation_checks: string[];
  ocr_confidence?: number | null;
}

export default function UnderwriterDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setResult(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) return;

    setIsAnalyzing(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/analyze`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResult(response.data);
    } catch (error) {
      console.error('Error analyzing document:', error);
      alert('Failed to analyze document. Make sure the backend is running.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getRiskColor = (score: number) => {
    if (score < 30) return 'text-green-500';
    if (score < 70) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getRiskBg = (score: number) => {
    if (score < 30) return 'bg-green-100 border-green-500';
    if (score < 70) return 'bg-yellow-100 border-yellow-500';
    return 'bg-red-100 border-red-500';
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-2">
              <ShieldAlert className="w-8 h-8 text-indigo-600" />
              Document Forensics System
            </h1>
            <p className="text-slate-500 mt-1">Underwriter Fraud Detection Dashboard</p>
          </div>
          <div className="flex gap-4">
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-lg shadow-sm text-slate-700 hover:bg-slate-50 transition-colors">
              <Settings className="w-4 h-4" /> Settings
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Upload and Original Image */}
          <div className="lg:col-span-1 flex flex-col gap-6">
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5 text-indigo-500" />
                Upload Document
              </h2>
              <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:border-indigo-500 transition-colors cursor-pointer relative">
                <input 
                  type="file" 
                  accept="image/*,application/pdf"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <FileText className="w-12 h-12 text-slate-400 mx-auto mb-3" />
                <p className="text-sm text-slate-600 font-medium">Click or drag file to upload</p>
                <p className="text-xs text-slate-400 mt-1">Supports PDF, JPG, PNG</p>
              </div>

              {file && (
                <button
                  onClick={handleAnalyze}
                  disabled={isAnalyzing}
                  className="w-full mt-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-lg shadow-sm transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isAnalyzing ? (
                    <><Activity className="w-5 h-5 animate-spin" /> Analyzing...</>
                  ) : (
                    <><Search className="w-5 h-5" /> Run Forensic Analysis</>
                  )}
                </button>
              )}
            </div>

            {preview && (
              <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex-1">
                <h3 className="font-medium text-slate-800 mb-3">Original Document</h3>
                <div className="bg-slate-100 rounded-lg overflow-hidden border border-slate-200 h-64 relative flex items-center justify-center">
                  <img src={preview} alt="Original" className="max-h-full max-w-full object-contain" />
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Results */}
          <div className="lg:col-span-2 flex flex-col gap-6">
            {result ? (
              <>
                {/* Score and Status */}
                <div className={`p-6 rounded-xl border-2 shadow-sm flex items-center justify-between ${getRiskBg(result.risk_score)}`}>
                  <div>
                    <h2 className="text-lg font-semibold text-slate-800 mb-1">Risk Assessment Score</h2>
                    <p className="text-sm text-slate-600">Based on multi-layer forensic analysis</p>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <span className={`text-4xl font-bold ${getRiskColor(result.risk_score)}`}>
                        {result.risk_score.toFixed(1)}%
                      </span>
                    </div>
                    {result.risk_score < 30 ? (
                      <CheckCircle className={`w-12 h-12 ${getRiskColor(result.risk_score)}`} />
                    ) : (
                      <AlertTriangle className={`w-12 h-12 ${getRiskColor(result.risk_score)}`} />
                    )}
                  </div>
                </div>

                {/* Heatmap and Anomalies Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Forensic Heatmap */}
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                      <Activity className="w-5 h-5 text-indigo-500" />
                      Forensic Heatmap (ELA)
                    </h3>
                    <div className="bg-slate-900 rounded-lg overflow-hidden border border-slate-700 h-64 flex items-center justify-center">
                      {result.heatmap_image_b64 ? (
                         <img src={`data:image/png;base64,${result.heatmap_image_b64}`} alt="ELA Heatmap" className="max-h-full max-w-full object-contain mix-blend-screen" />
                      ) : (
                        <p className="text-slate-500 text-sm">No heatmap generated.</p>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                      Highlights areas of inconsistent compression. Bright spots indicate potential manipulation.
                    </p>
                  </div>

                  {/* Anomalies Detected */}
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col">
                    <h3 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-red-500" />
                      Anomalies Detected
                    </h3>
                    <div className="flex-1 bg-slate-50 border border-slate-200 rounded-lg p-4 overflow-y-auto">
                      {result.anomalies.length > 0 ? (
                        <ul className="space-y-3">
                          {result.anomalies.map((anomaly, idx) => (
                            <li key={idx} className="flex gap-3 text-sm text-slate-700 bg-white p-3 rounded shadow-sm border border-slate-100">
                              <span className="text-red-500 mt-0.5">•</span>
                              <span>{anomaly}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <div className="h-full flex items-center justify-center text-slate-500 text-sm">
                          <CheckCircle className="w-4 h-4 mr-2 text-green-500" /> No anomalies detected.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Additional Details */}
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                  <h3 className="font-semibold text-slate-800 mb-4">Local Validation & Metadata</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2">Validation Engine</h4>
                      <div className="bg-indigo-50 border border-indigo-100 text-indigo-800 text-sm p-3 rounded-lg">
                        <p>{result.validation_status}</p>
                        {typeof result.ocr_confidence === 'number' && (
                          <p className="text-xs mt-2 text-indigo-600">OCR confidence: {result.ocr_confidence.toFixed(1)}%</p>
                        )}
                        {result.validation_checks?.length > 0 && (
                          <ul className="list-disc list-inside text-xs mt-2 space-y-1">
                            {result.validation_checks.map((check, idx) => (
                              <li key={idx}>{check}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-2">Suspicious Metadata Tags</h4>
                      <div className="bg-slate-50 border border-slate-200 text-sm p-3 rounded-lg min-h-[44px]">
                        {Object.entries(result.metadata).length > 0 ? (
                          <ul className="list-disc list-inside text-slate-700">
                            {Object.entries(result.metadata).map(([key, val]) => (
                              <li key={key}><span className="font-medium">{key}:</span> {val}</li>
                            ))}
                          </ul>
                        ) : (
                          <span className="text-slate-400">None detected.</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-full flex items-center justify-center bg-white rounded-xl shadow-sm border border-slate-200 p-12 text-center text-slate-400">
                <div>
                  <Search className="w-16 h-16 mx-auto mb-4 opacity-20" />
                  <p className="text-lg">Upload a document and run analysis to view forensic insights.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
