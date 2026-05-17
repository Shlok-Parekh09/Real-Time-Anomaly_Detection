import React, { useMemo, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bot,
  Check,
  CheckCircle,
  ChevronRight,
  Clock,
  Database,
  Eye,
  File,
  FileText,
  Layers,
  RotateCcw,
  Search,
  Settings,
  ShieldAlert,
  Upload,
  XCircle,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const ACCEPTED_FILES = '.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.xlsx,.xlsm,.xltx,.xltm,.xls,.csv,.tsv,application/pdf,image/*,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,text/csv,text/tab-separated-values';

interface FraudSignal {
  id: string;
  name: string;
  severity: 'high' | 'medium' | 'low' | string;
  summary: string;
  description: string;
  evidence: string[];
  confidence: number;
  recovered_version_available?: boolean;
}

interface RecoveredChange {
  field: string;
  previous_value: string;
  current_value: string;
  type: string;
}

interface RecoveredSection {
  title: string;
  items: string[];
}

interface RecoveredVersion {
  available: boolean;
  title: string;
  summary: string;
  method: string;
  preview_text: string;
  sections: RecoveredSection[];
  changes: RecoveredChange[];
  confidence: number;
}

interface AiExplanation {
  summary: string;
  likely_alteration: string;
  recommended_action: string;
  limitations: string;
  generated_by: string;
}

interface AnalysisResult {
  file_name: string;
  file_type: string;
  risk_score: number;
  trust_score: number;
  anomalies: string[];
  fraud_signals: FraudSignal[];
  recovered_version: RecoveredVersion;
  ai_explanation: AiExplanation;
  metadata: Record<string, unknown>;
  feature_summary: Record<string, unknown>;
  extracted_text: string;
  validation_status: string;
  validation_checks: string[];
  ocr_confidence?: number | null;
}

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function formatBytes(bytes?: number) {
  if (!bytes) return '0 KB';
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function friendlyType(file: File | null, result: AnalysisResult | null) {
  const type = result?.file_type;
  if (type === 'excel') return 'Spreadsheet';
  if (type === 'pdf') return 'PDF';
  if (type === 'image') return 'Image';
  if (!file) return 'Unknown';
  if (file.name.toLowerCase().match(/\.(xlsx|xlsm|xltx|xltm|xls|csv|tsv)$/)) return 'Spreadsheet';
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return 'PDF';
  if (file.type.startsWith('image/')) return 'Image';
  return 'Document';
}

function metadataValue(value: unknown) {
  if (Array.isArray(value)) return value.length ? value.join(', ') : 'None';
  if (typeof value === 'object' && value !== null) return JSON.stringify(value);
  return String(value ?? '');
}

function severityStyles(severity: string) {
  if (severity === 'high') {
    return {
      title: 'High Severity',
      shell: 'bg-red-50 text-red-700 border-red-100',
      icon: 'bg-red-100 text-red-600',
      dot: 'bg-red-500',
    };
  }
  if (severity === 'medium') {
    return {
      title: 'Medium Severity',
      shell: 'bg-amber-50 text-amber-700 border-amber-100',
      icon: 'bg-amber-100 text-amber-600',
      dot: 'bg-amber-500',
    };
  }
  return {
    title: 'Low Severity',
    shell: 'bg-slate-50 text-slate-600 border-slate-100',
    icon: 'bg-slate-100 text-slate-500',
    dot: 'bg-slate-400',
  };
}

function SignalRow({
  signal,
  selected,
  onClick,
}: {
  signal: FraudSignal;
  selected: boolean;
  onClick: () => void;
}) {
  const styles = severityStyles(signal.severity);
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'w-full text-left rounded-lg border p-3 transition-colors',
        selected ? 'border-violet-300 bg-violet-50' : 'border-transparent bg-white hover:border-slate-200'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={cx('mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full', styles.icon)}>
          <AlertTriangle className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-bold text-slate-900">{signal.name}</p>
            {signal.recovered_version_available && (
              <span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold text-violet-700">
                X-ray
              </span>
            )}
          </div>
          <p className="mt-0.5 text-xs leading-snug text-slate-500">{signal.summary}</p>
        </div>
        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-slate-300" />
      </div>
    </button>
  );
}

function DocumentPreview({
  file,
  previewUrl,
  result,
  mode,
}: {
  file: File | null;
  previewUrl: string | null;
  result: AnalysisResult | null;
  mode: 'document' | 'xray';
}) {
  const rows = useMemo(
    () => (result?.extracted_text || '').split('\n').filter(Boolean).slice(0, 28),
    [result?.extracted_text]
  );
  const kind = friendlyType(file, result).toLowerCase();
  const [reveal, setReveal] = useState(48);

  if (mode === 'xray' && result) {
    const recovered = result.recovered_version;
    const primaryChanges = recovered.changes.slice(0, 4);
    const previousPrimary = primaryChanges[0]?.previous_value || 'Recovered previous value';
    const currentPrimary = primaryChanges[0]?.current_value || 'Submitted document value';
    const previousSecondary = primaryChanges[1]?.previous_value || 'Original account holder';
    const currentSecondary = primaryChanges[1]?.current_value || 'Submitted account holder';
    return (
      <div className="grid h-full gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-violet-700">X-ray Signal</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{recovered.title}</p>
            </div>
            <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-bold text-violet-700">
              {Math.round((recovered.confidence || 0) * 100)}% confidence
            </span>
          </div>

          <div className="bg-[#edeaf3] p-5">
            <div className="relative mx-auto min-h-[560px] max-w-[820px] overflow-hidden bg-black shadow-lg">
              <div className="absolute inset-0 bg-white p-10 text-slate-950">
                <div className="mb-10 flex items-start justify-between">
                  <div>
                    <p className="text-3xl font-black tracking-tight">Recovered Bank Statement</p>
                    <p className="text-sm font-semibold text-slate-500">Submitted version</p>
                  </div>
                  <div className="rounded bg-red-700 px-4 py-3 text-sm font-black text-white">BANK</div>
                </div>
                <div className="grid grid-cols-2 gap-8">
                  <div className="space-y-5">
                    <div className="inline-block border-2 border-red-400 bg-red-100 px-5 py-3 text-sm font-bold text-red-950">
                      {currentPrimary}
                    </div>
                    <div className="border-t-4 border-slate-900 pt-3">
                      <p className="text-2xl font-black">Important Account Information</p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-700">
                        Submitted document layer after the final incremental update.
                      </p>
                    </div>
                  </div>
                  <div className="space-y-5">
                    <div className="border-l-4 border-slate-900 pl-4">
                      <p className="text-xl font-black">Questions?</p>
                      <p className="mt-2 text-sm leading-relaxed">Available by phone 24 hours a day, 7 days a week.</p>
                    </div>
                    <div className="border-t-4 border-slate-900 pt-3">
                      <p className="text-xl font-black">Account options</p>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                        <span>Online Banking</span><span>Checked</span>
                        <span>Direct Deposit</span><span>Checked</span>
                        <span>Account holder</span><span>{currentSecondary}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div
                className="absolute inset-y-0 left-0 overflow-hidden bg-black text-white"
                style={{ width: `${reveal}%` }}
              >
                <div className="h-full w-[820px] p-10 opacity-90">
                  <div className="mb-10 flex items-start justify-between">
                    <div>
                      <p className="text-3xl font-black tracking-tight text-white/80">Recovered Bank Statement</p>
                      <p className="text-sm font-semibold text-white/50">Previous version layer</p>
                    </div>
                    <div className="rounded border border-white/20 px-4 py-3 text-sm font-black text-white/70">BANK</div>
                  </div>
                  <div className="grid grid-cols-2 gap-8">
                    <div className="space-y-5">
                      <div className="inline-block border border-white/80 bg-white/20 px-5 py-3 text-sm font-bold text-white">
                        {previousPrimary}
                      </div>
                      <div className="border-t-4 border-white/40 pt-3">
                        <p className="text-2xl font-black text-white/80">Important Account Information</p>
                        <p className="mt-2 text-sm leading-relaxed text-white/55">
                          The recovered layer shows content present before the submitted revision.
                        </p>
                      </div>
                    </div>
                    <div className="space-y-5">
                      <div className="border-l-4 border-white/40 pl-4">
                        <p className="text-xl font-black text-white/80">Questions?</p>
                        <p className="mt-2 text-sm leading-relaxed text-white/55">Recovered text is dimmed for comparison.</p>
                      </div>
                      <div className="border-t-4 border-white/40 pt-3">
                        <p className="text-xl font-black text-white/80">Account options</p>
                        <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-white/60">
                          <span>Online Banking</span><span>Checked</span>
                          <span>Direct Deposit</span><span>Checked</span>
                          <span>Account holder</span><span>{previousSecondary}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="absolute inset-y-0" style={{ left: `${reveal}%` }}>
                <div className="h-full w-1 bg-white shadow-[0_0_20px_rgba(255,255,255,0.85)]" />
                <div className="absolute top-1/2 -ml-5 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-slate-900 text-white shadow-lg">
                  <ChevronRight className="h-5 w-5 rotate-180" />
                  <ChevronRight className="-ml-2 h-5 w-5" />
                </div>
              </div>

              {primaryChanges.length > 0 && (
                <div className="absolute left-[9%] top-[18%] h-16 w-52 border-2 border-white/80 bg-white/10" />
              )}
              {primaryChanges.length > 1 && (
                <div className="absolute bottom-[12%] right-[12%] h-14 w-56 border-2 border-white/70 bg-white/10" />
              )}
            </div>

            <input
              aria-label="X-ray reveal"
              type="range"
              min={18}
              max={82}
              value={reveal}
              onChange={(event) => setReveal(Number(event.target.value))}
              className="mx-auto mt-4 block w-full max-w-[520px] accent-violet-700"
            />
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">How It Was Altered</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{recovered.method}</p>
          </div>
          <div className="h-[620px] overflow-auto p-4">
            <p className="mb-4 rounded-lg bg-violet-50 p-3 text-sm leading-relaxed text-violet-950">
              {recovered.summary}
            </p>
            {recovered.changes.length > 0 ? (
              <div className="space-y-3">
                {recovered.changes.map((change, index) => (
                  <div key={`${change.field}-${index}`} className="rounded-lg border border-slate-200 bg-white p-3">
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-xs font-bold text-slate-500">{change.field}</p>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-500">
                        {change.type}
                      </span>
                    </div>
                    <div className="space-y-2">
                      <div className="rounded-md bg-red-50 p-2">
                        <p className="mb-1 text-[10px] font-bold uppercase text-red-600">Previous</p>
                        <p className="text-xs leading-relaxed text-red-950">{change.previous_value}</p>
                      </div>
                      <div className="rounded-md bg-emerald-50 p-2">
                        <p className="mb-1 text-[10px] font-bold uppercase text-emerald-600">Submitted</p>
                        <p className="text-xs leading-relaxed text-emerald-950">{change.current_value}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex h-72 items-center justify-center text-center text-sm text-slate-500">
                <div>
                  <Eye className="mx-auto mb-3 h-8 w-8 text-slate-300" />
                  <p>No previous-version edits were recovered.</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    );
  }

  if (!file || !previewUrl) {
    return (
      <div className="flex h-full min-h-[520px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-center">
        <div>
          <FileText className="mx-auto mb-4 h-12 w-12 text-slate-300" />
          <p className="text-sm font-semibold text-slate-700">Upload a document to inspect it</p>
          <p className="mt-1 text-xs text-slate-400">PDF, image, Excel, CSV, and TSV are supported.</p>
        </div>
      </div>
    );
  }

  if (kind === 'image') {
    return (
      <div className="flex h-full min-h-[520px] items-center justify-center overflow-auto rounded-lg border border-slate-200 bg-white p-6">
        <img src={previewUrl} alt="Uploaded document" className="max-h-[760px] max-w-full object-contain shadow-sm" />
      </div>
    );
  }

  if (kind === 'pdf') {
    return (
      <div className="h-full min-h-[620px] overflow-hidden rounded-lg border border-slate-200 bg-white">
        <iframe title="PDF preview" src={previewUrl} className="h-full min-h-[620px] w-full" />
      </div>
    );
  }

  return (
    <div className="h-full min-h-[520px] overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Spreadsheet Preview</p>
        <p className="mt-1 text-sm font-semibold text-slate-900">{file.name}</p>
      </div>
      <div className="h-[560px] overflow-auto p-4">
        {rows.length > 0 ? (
          <div className="space-y-1 font-mono text-xs text-slate-700">
            {rows.map((row, index) => (
              <div key={`${row}-${index}`} className={cx('rounded px-3 py-2', row.startsWith('[') ? 'bg-violet-50 font-bold text-violet-700' : 'bg-slate-50')}>
                {row}
              </div>
            ))}
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-center text-sm text-slate-500">
            <div>
              <Database className="mx-auto mb-3 h-9 w-9 text-slate-300" />
              <p>Run forensics to render the workbook preview and X-ray traces.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function UnderwriterDashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'document' | 'xray'>('document');

  const selectedSignal = useMemo(() => {
    if (!result?.fraud_signals.length) return null;
    return result.fraud_signals.find((signal) => signal.id === selectedSignalId) ?? result.fraud_signals[0];
  }, [result?.fraud_signals, selectedSignalId]);

  const groupedSignals = useMemo(() => {
    const groups: Record<string, FraudSignal[]> = { high: [], medium: [], low: [] };
    result?.fraud_signals.forEach((signal) => {
      const key = signal.severity === 'high' || signal.severity === 'medium' ? signal.severity : 'low';
      groups[key].push(signal);
    });
    return groups;
  }, [result?.fraud_signals]);

  const parsedDetails = useMemo(() => {
    if (!result) return [];
    const preferred = ['page_count', 'sheet_count', 'formula_count', 'hidden_sheets', 'unused_shared_string_count', 'Creator', 'Producer', 'created', 'modified'];
    return preferred
      .filter((key) => result.metadata[key] !== undefined && result.metadata[key] !== '')
      .map((key) => [key, metadataValue(result.metadata[key])] as const)
      .slice(0, 8);
  }, [result]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0];
    if (!selected) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setResult(null);
    setSelectedSignalId(null);
    setViewMode('document');
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setViewMode('document');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const data = (await response.json()) as AnalysisResult;
      setResult(data);
      setSelectedSignalId(data.fraud_signals[0]?.id ?? null);
      if (data.recovered_version.available) {
        setViewMode('xray');
      }
    } catch (error) {
      console.error('Error analyzing document:', error);
      alert('Failed to analyze document. Make sure the backend is running and CORS is enabled.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const trustScore = result?.trust_score ?? 0;
  const riskLabel = !result ? 'Awaiting Scan' : trustScore >= 70 ? 'Low Risk' : trustScore >= 35 ? 'Review Required' : 'High Risk';

  return (
    <div className="min-h-screen bg-[#f8f6fb] text-slate-950">
      <header className="sticky top-0 z-30 flex h-[62px] items-center justify-between border-b border-slate-200 bg-white px-5">
        <div className="flex min-w-0 items-center gap-3">
          <button className="rounded-full p-2 text-slate-500 hover:bg-slate-100" type="button" aria-label="Back">
            <ChevronRight className="h-5 w-5 rotate-180" />
          </button>
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-violet-100 text-violet-700">
            <File className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-slate-900">{file?.name ?? 'Document Forensics'}</p>
            <p className="text-xs text-slate-500">
              {file ? `${friendlyType(file, result)} - ${formatBytes(file.size)}` : 'Upload a file to begin'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button className="hidden rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 sm:flex" type="button">
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </button>
          <button className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" type="button">
            <XCircle className="mr-2 inline h-4 w-4" />
            Reject
          </button>
          <button className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-bold text-white hover:bg-slate-800" type="button">
            <Check className="mr-2 inline h-4 w-4" />
            Accept
          </button>
        </div>
      </header>

      <main className="grid min-h-[calc(100vh-62px)] grid-cols-1 xl:grid-cols-[280px_1fr_390px]">
        <aside className="border-r border-slate-200 bg-white">
          <section className="border-b border-slate-200 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-black text-slate-900">Document</h2>
              <Clock className="h-4 w-4 text-slate-400" />
            </div>
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs font-semibold text-slate-400">Uploaded</p>
                <p className="font-bold text-slate-800">{file ? new Date().toLocaleString() : 'Not uploaded'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400">Format</p>
                <p className="font-bold text-slate-800">{friendlyType(file, result)}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-400">Quality Score</p>
                <p className="font-bold text-slate-800">{result ? result.trust_score.toFixed(1) : '--'}</p>
              </div>
            </div>
          </section>

          <section className="border-b border-slate-200 p-5">
            <h2 className="mb-4 text-sm font-black text-slate-900">Upload</h2>
            <div className="relative rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 p-5 text-center hover:border-violet-300">
              <input
                type="file"
                accept={ACCEPTED_FILES}
                onChange={handleFileChange}
                className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
              />
              <Upload className="mx-auto mb-2 h-8 w-8 text-slate-300" />
              <p className="text-sm font-bold text-slate-700">{file ? 'Replace file' : 'Browse files'}</p>
              <p className="mt-1 text-xs text-slate-400">PDF, image, Excel, CSV, TSV</p>
            </div>
            <button
              onClick={handleAnalyze}
              disabled={!file || isAnalyzing}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-700 px-4 py-3 text-sm font-bold text-white shadow-sm transition-colors hover:bg-violet-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              type="button"
            >
              {isAnalyzing ? (
                <>
                  <Activity className="h-4 w-4 animate-spin" />
                  Running forensics
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" />
                  Run Forensics
                </>
              )}
            </button>
          </section>

          <section className="p-5">
            <h2 className="mb-4 text-sm font-black text-slate-900">Parsed Details</h2>
            {parsedDetails.length > 0 ? (
              <div className="space-y-3">
                {parsedDetails.map(([key, value]) => (
                  <div key={key}>
                    <p className="text-xs font-semibold capitalize text-slate-400">{key.replace(/_/g, ' ')}</p>
                    <p className="break-words text-sm font-bold text-slate-800">{value}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Details appear after analysis.</p>
            )}
          </section>
        </aside>

        <section className="min-w-0 bg-[#f5f2fa] p-4 lg:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">
              <button
                type="button"
                onClick={() => setViewMode('document')}
                className={cx('rounded-md px-3 py-1.5 text-sm font-bold', viewMode === 'document' ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-50')}
              >
                Document
              </button>
              <button
                type="button"
                onClick={() => setViewMode('xray')}
                className={cx('rounded-md px-3 py-1.5 text-sm font-bold', viewMode === 'xray' ? 'bg-violet-700 text-white' : 'text-slate-500 hover:bg-slate-50')}
              >
                X-ray Signal
              </button>
            </div>
            {result && (
              <div className="flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-500">
                <Layers className="h-4 w-4 text-violet-600" />
                {result.recovered_version.available ? 'Previous version recovered' : 'No previous version recovered'}
              </div>
            )}
          </div>
          <DocumentPreview file={file} previewUrl={previewUrl} result={result} mode={viewMode} />
        </section>

        <aside className="border-l border-slate-200 bg-white">
          <section className="border-b border-slate-200 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-black text-slate-900">Trust Score</h2>
              <ShieldAlert className="h-4 w-4 text-slate-400" />
            </div>
            <div className="flex items-center gap-4">
              <div className={cx('flex h-12 w-12 items-center justify-center rounded-full text-lg font-black text-white', trustScore >= 70 ? 'bg-emerald-500' : trustScore >= 35 ? 'bg-amber-500' : 'bg-red-500')}>
                {result ? Math.round(trustScore) : '--'}
              </div>
              <div className="flex-1">
                <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={cx('h-full rounded-full', trustScore >= 70 ? 'bg-emerald-500' : trustScore >= 35 ? 'bg-amber-500' : 'bg-red-500')}
                    style={{ width: `${result ? trustScore : 0}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-[10px] font-bold text-slate-400">
                  <span>0</span>
                  <span>50</span>
                  <span>100</span>
                </div>
              </div>
            </div>
            <p className="mt-3 text-sm font-bold text-slate-800">{riskLabel}</p>
          </section>

          <section className="border-b border-slate-200 p-5">
            <button type="button" className="flex w-full items-center justify-between rounded-lg border border-slate-200 p-4 text-left hover:bg-slate-50">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-violet-100 text-violet-700">
                  <Database className="h-4 w-4" />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-900">Similar Documents</p>
                  <p className="text-xs text-slate-500">Compare against trusted submissions</p>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-slate-300" />
            </button>
          </section>

          <section className="border-b border-slate-200 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-black text-slate-900">Fraud Signals</h2>
              <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">
                {result?.fraud_signals.length ?? 0} Detected
              </span>
            </div>
            {result ? (
              <div className="space-y-4">
                {(['high', 'medium', 'low'] as const).map((severity) => {
                  const items = groupedSignals[severity];
                  if (!items.length) return null;
                  const styles = severityStyles(severity);
                  return (
                    <div key={severity}>
                      <div className={cx('mb-2 rounded-md border px-3 py-2 text-xs font-bold', styles.shell)}>
                        <span className={cx('mr-2 inline-block h-2 w-2 rounded-full', styles.dot)} />
                        {styles.title}
                      </div>
                      <div className="space-y-2">
                        {items.map((signal) => (
                          <SignalRow
                            key={`${signal.id}-${signal.summary}`}
                            signal={signal}
                            selected={selectedSignal?.id === signal.id && selectedSignal?.summary === signal.summary}
                            onClick={() => {
                              setSelectedSignalId(signal.id);
                              if (signal.recovered_version_available) setViewMode('xray');
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  );
                })}
                {result.fraud_signals.length === 0 && (
                  <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">
                    <CheckCircle className="mb-2 h-5 w-5" />
                    No fraud signals detected.
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Run forensics to populate signals.</p>
            )}
          </section>

          <section className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <Bot className="h-4 w-4 text-violet-600" />
              <h2 className="text-sm font-black text-slate-900">AI Explanation</h2>
            </div>
            {result ? (
              <div className="space-y-3 text-sm">
                <p className="rounded-lg bg-violet-50 p-3 leading-relaxed text-violet-950">{result.ai_explanation.summary}</p>
                <div>
                  <p className="text-xs font-bold uppercase text-slate-400">Likely alteration</p>
                  <p className="mt-1 leading-relaxed text-slate-700">{result.ai_explanation.likely_alteration}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-slate-400">Recommended action</p>
                  <p className="mt-1 leading-relaxed text-slate-700">{result.ai_explanation.recommended_action}</p>
                </div>
                <p className="text-xs text-slate-400">Generated by {result.ai_explanation.generated_by}</p>
              </div>
            ) : (
              <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
                Cerebras-generated descriptions appear here when the backend has CEREBRAS_API_KEY set.
              </div>
            )}
          </section>

          {result && (
            <section className="border-t border-slate-200 p-5">
              <button
                onClick={() => {
                  setResult(null);
                  setSelectedSignalId(null);
                  setViewMode('document');
                }}
                className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 px-4 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50"
                type="button"
              >
                <RotateCcw className="h-4 w-4" />
                Reset Report
              </button>
            </section>
          )}
        </aside>
      </main>
    </div>
  );
}
