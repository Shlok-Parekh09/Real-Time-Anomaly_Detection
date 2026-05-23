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
  MoveHorizontal,
  RotateCcw,
  Search,
  Settings,
  ShieldAlert,
  Upload,
  XCircle,
} from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const ACCEPTED_FILES = '.pdf,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,application/pdf,image/*';

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
  feature_summary: {
    file_type: string;
    signal_count: number;
    high_severity: number;
    medium_severity: number;
    low_severity: number;
    highlight_coordinates?: HighlightCoordinate[];
  };
  extracted_text: string;
  validation_status: string;
  validation_checks: string[];
  ocr_confidence?: number | null;
  converted_to_pdf?: boolean;
  pdf_data_base64?: string | null;
}

interface HighlightCoordinate {
  page: number;
  bbox: {
    x: number;  // percentage
    y: number;  // percentage
    width: number;  // percentage
    height: number;  // percentage
  };
  severity: 'high' | 'medium' | 'low';
  signal_name: string;
  signal_id: string;
  texts: string[];
}

type ReviewDecision = 'accepted' | 'rejected';

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
  if (type === 'pdf') return 'PDF';
  if (type === 'image') return 'Image';
  if (type === 'word') return 'Word';
  if (type === 'excel') return 'Excel';
  if (!file) return 'Unknown';
  if (file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf')) return 'PDF';
  if (file.type.startsWith('image/')) return 'Image';
  if (file.name.toLowerCase().endsWith('.doc') || file.name.toLowerCase().endsWith('.docx')) return 'Word';
  if (file.name.toLowerCase().endsWith('.xls') || file.name.toLowerCase().endsWith('.xlsx')) return 'Excel';
  return 'Document';
}

function isSupportedUpload(file: File) {
  const lowerName = file.name.toLowerCase();
  return (
    file.type === 'application/pdf' ||
    file.type.startsWith('image/') ||
    lowerName.endsWith('.pdf') ||
    /\.(png|jpe?g|webp|bmp|tiff?)$/.test(lowerName)
  );
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

interface VisualRegion {
  label: string;
  severity: 'high' | 'medium' | 'low';
  top: string;
  left: string;
  width: string;
  height: string;
}

const REGION_LAYOUT: Array<Omit<VisualRegion, 'label' | 'severity'>> = [
  { top: '17%', left: '10%', width: '28%', height: '9%' },
  { top: '78%', left: '62%', width: '25%', height: '7%' },
  { top: '36%', left: '12%', width: '45%', height: '6%' },
  { top: '61%', left: '58%', width: '28%', height: '6%' },
  { top: '24%', left: '63%', width: '20%', height: '8%' },
  { top: '82%', left: '14%', width: '25%', height: '7%' },
];

function pdfViewerUrl(previewUrl: string) {
  // Disable zoom, fit to page width, hide toolbar and navigation
  return `${previewUrl}#toolbar=0&navpanes=0&scrollbar=1&view=FitH&zoom=page-fit&pagemode=none`;
}

function buildVisualRegions(result: AnalysisResult | null): VisualRegion[] {
  // Use actual coordinates from backend if available
  const coordinates = result?.feature_summary?.highlight_coordinates || [];
  
  if (coordinates.length > 0) {
    return coordinates.map((coord) => ({
      label: coord.signal_name || 'Fraud Signal',
      severity: coord.severity,
      top: `${coord.bbox.y}%`,
      left: `${coord.bbox.x}%`,
      width: `${coord.bbox.width}%`,
      height: `${coord.bbox.height}%`,
    }));
  }

  // Fallback to changes if no coordinates
  const changes = result?.recovered_version?.changes ?? [];
  if (changes.length) {
    return changes.slice(0, REGION_LAYOUT.length).map((change, index) => ({
      ...REGION_LAYOUT[index],
      label: change.field || `Recovered change ${index + 1}`,
      severity: change.type === 'removed' ? 'high' : 'medium',
    }));
  }

  // Fallback to fraud signals with predefined layout
  return (result?.fraud_signals ?? []).slice(0, REGION_LAYOUT.length).map((signal, index) => ({
    ...REGION_LAYOUT[index],
    label: signal.name,
    severity: signal.severity === 'high' || signal.severity === 'medium' ? signal.severity : 'low',
  }));
}

function EvidenceOverlay({ regions, containerRef }: { regions: VisualRegion[]; containerRef?: React.RefObject<HTMLDivElement | null> }) {
  if (!regions.length) return null;
  
  return (
    <div className="pointer-events-none absolute inset-0" style={{ width: '100%', height: '100%' }}>
      {regions.map((region, index) => {
        // Determine colors based on severity - using semi-transparent highlights
        const isHighSeverity = region.severity === 'high';
        const isMediumSeverity = region.severity === 'medium';
        
        // Use highlight-style colors (more transparent, no borders)
        const bgColor = isHighSeverity 
          ? 'bg-red-400/40' 
          : isMediumSeverity 
            ? 'bg-yellow-300/50' 
            : 'bg-slate-300/30';
        
        const labelBg = isHighSeverity ? 'bg-red-600' : isMediumSeverity ? 'bg-yellow-600' : 'bg-slate-600';
        
        return (
          <div
            key={`${region.label}-${index}`}
            className={`absolute ${bgColor}`}
            style={{
              top: region.top,
              left: region.left,
              width: region.width,
              height: region.height,
              mixBlendMode: 'multiply',  // Blend with underlying content
              borderRadius: '2px',
            }}
            title={region.label}
          >
            {/* Small label indicator */}
            <span 
              className={`absolute -top-5 left-0 max-w-32 truncate rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-white shadow-sm ${labelBg}`}
              style={{ fontSize: '8px' }}
            >
              {region.label}
            </span>
          </div>
        );
      })}
    </div>
  );
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
          {selected && signal.description && (
            <p className="mt-2 rounded-md bg-slate-50 p-2 text-xs leading-relaxed text-slate-600 border border-slate-100">
              {signal.description}
            </p>
          )}
        </div>
        <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-slate-300" />
      </div>
    </button>
  );
}

function PdfFrame({ previewUrl, title, className }: { previewUrl: string; title: string; className?: string }) {
  return (
    <iframe
      title={title}
      src={pdfViewerUrl(previewUrl)}
      className={cx('h-full w-full border-0 bg-white', className)}
      loading="lazy"
      style={{
        pointerEvents: 'auto',
        touchAction: 'pan-y pan-x',
        overflow: 'hidden',
      }}
    />
  );
}

function OriginalVersionLayer({ result, kind, file }: { result: AnalysisResult; kind: string; file?: File }) {
  const recovered = result.recovered_version;
  const originalRows = (recovered.preview_text || '')
    .split('\n')
    .filter(Boolean)
    .slice(0, 34);
  const fallbackRows = recovered.changes.slice(0, 12).map((change) => `${change.field}: ${change.previous_value}`);
  const rows = originalRows.length ? originalRows : fallbackRows;

  // For Word/Excel with recovered content, show the recovered text in a styled view
  if ((kind === 'word' || kind === 'excel') && rows.length > 0) {
    return (
      <div className="flex h-full items-center justify-center overflow-auto bg-[#e9f8f1] p-6">
        <div className="min-h-[86%] w-[min(720px,92%)] rounded-sm border border-emerald-200 bg-white p-8 shadow-2xl">
          <div className="mb-6 flex items-center justify-between border-b border-emerald-100 pb-4">
            <div>
              <p className="text-[10px] font-black uppercase tracking-wide text-emerald-600">Original recovered</p>
              <p className="mt-1 text-sm font-bold text-slate-900">{recovered.title}</p>
            </div>
            <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-black text-emerald-700">
              X-ray
            </span>
          </div>
          <div className="space-y-2 font-mono text-xs leading-relaxed text-slate-700">
            {rows.map((row, index) => (
              <p key={`${row}-${index}`} className="border-b border-slate-100 pb-2">
                {row}
              </p>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full items-center justify-center overflow-auto bg-[#e9f8f1] p-6">
      <div className="min-h-[86%] w-[min(720px,92%)] rounded-sm border border-emerald-200 bg-white p-8 shadow-2xl">
        <div className="mb-6 flex items-center justify-between border-b border-emerald-100 pb-4">
          <div>
            <p className="text-[10px] font-black uppercase tracking-wide text-emerald-600">Original recovered</p>
            <p className="mt-1 text-sm font-bold text-slate-900">{recovered.title}</p>
          </div>
          <span className="rounded-full bg-emerald-100 px-2 py-1 text-[10px] font-black text-emerald-700">
            X-ray
          </span>
        </div>
        {rows.length ? (
          <div className="space-y-2 font-mono text-xs leading-relaxed text-slate-700">
            {rows.map((row, index) => (
              <p key={`${row}-${index}`} className="border-b border-slate-100 pb-2">
                {row}
              </p>
            ))}
          </div>
        ) : (
          <div className="flex min-h-[420px] items-center justify-center text-center text-sm text-slate-500">
            <div>
              <Eye className="mx-auto mb-3 h-9 w-9 text-emerald-300" />
              <p>No recoverable original page image was found.</p>
              <p className="mt-1 text-xs text-slate-400">The submitted document stays visible on the fraud side.</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SubmittedVersionLayer({
  kind,
  previewUrl,
  rows,
  xrayFilter,
  file,
  result,
}: {
  kind: string;
  previewUrl: string;
  rows: string[];
  xrayFilter?: boolean;
  file?: File;
  result?: AnalysisResult | null;
}) {
  const filterStyle = xrayFilter
    ? { filter: 'invert(0.88) contrast(1.25) hue-rotate(180deg) saturate(0.3) brightness(1.1)' }
    : undefined;

  // If Word document was converted to PDF, treat it as PDF
  const isConvertedPdf = result?.converted_to_pdf || false;
  const effectiveKind = isConvertedPdf ? 'pdf' : kind;

  if (effectiveKind === 'image') {
    return (
      <div className="relative h-full w-full overflow-hidden bg-neutral-900">
        <img
          src={previewUrl}
          alt="Submitted document preview"
          className="h-full w-full object-contain"
          style={filterStyle}
        />
      </div>
    );
  }

  if (effectiveKind === 'pdf') {
    return (
      <div className="h-full w-full" style={filterStyle}>
        <PdfFrame title="Submitted fraud PDF preview" previewUrl={previewUrl} />
      </div>
    );
  }

  if ((effectiveKind === 'word' || effectiveKind === 'excel') && file) {
    return <DocxPreview file={file} xrayFilter={xrayFilter} />;
  }

  return (
    <div className="h-full overflow-auto bg-neutral-900 p-6" style={filterStyle}>
      <div className="min-w-[760px] rounded bg-white p-4 font-mono text-xs text-slate-800">
        {rows.length > 0 ? (
          rows.map((row, index) => (
            <div key={`${row}-${index}`} className="border-b border-slate-100 px-2 py-1">
              {row}
            </div>
          ))
        ) : (
          <div className="flex h-[460px] items-center justify-center text-center text-sm text-slate-500">
            Document text appears after forensics completes.
          </div>
        )}
      </div>
    </div>
  );
}

function XrayComparison({
  kind,
  previewUrl,
  result,
  rows,
  regions,
  showEvidenceMarkers,
  previewHeight,
  file,
}: {
  kind: string;
  previewUrl: string;
  result: AnalysisResult;
  rows: string[];
  regions: VisualRegion[];
  showEvidenceMarkers: boolean;
  previewHeight: string;
  file?: File;
}) {
  const [reveal, setReveal] = useState(0); // Start at 0 (full color view)
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const normalLayerRef = React.useRef<HTMLDivElement | null>(null);
  const xrayLayerRef = React.useRef<HTMLDivElement | null>(null);

  // Synchronize scroll between both layers
  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const source = event.currentTarget;
    const scrollTop = source.scrollTop;
    const scrollLeft = source.scrollLeft;

    // Sync to the other layer
    if (normalLayerRef.current && source !== normalLayerRef.current) {
      normalLayerRef.current.scrollTop = scrollTop;
      normalLayerRef.current.scrollLeft = scrollLeft;
    }
    if (xrayLayerRef.current && source !== xrayLayerRef.current) {
      xrayLayerRef.current.scrollTop = scrollTop;
      xrayLayerRef.current.scrollLeft = scrollLeft;
    }
  };

  const updateRevealFromClientX = (clientX: number) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect || rect.width <= 0) return;
    const next = ((clientX - rect.left) / rect.width) * 100;
    setReveal(Math.max(0, Math.min(100, next)));
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      setReveal((current) => Math.max(0, current - 4));
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      setReveal((current) => Math.min(100, current + 4));
    }
    if (event.key === 'Home') {
      event.preventDefault();
      setReveal(0);
    }
    if (event.key === 'End') {
      event.preventDefault();
      setReveal(100);
    }
  };

  return (
    <div ref={containerRef} className={cx('relative overflow-hidden bg-neutral-900', previewHeight)}>
      {/* Normal colored version (base layer) - scrollable - NO HIGHLIGHTS */}
      <div 
        ref={normalLayerRef}
        className="relative h-full w-full overflow-auto"
        onScroll={handleScroll}
      >
        <SubmittedVersionLayer kind={kind} previewUrl={previewUrl} rows={rows} xrayFilter={false} file={file} result={result} />
      </div>
      
      {/* X-ray filtered version with highlights (revealed from left to right) - scrollable */}
      <div
        ref={xrayLayerRef}
        className="absolute inset-0 overflow-auto"
        style={{ 
          clipPath: `inset(0 ${100 - reveal}% 0 0)`,
          pointerEvents: reveal > 0 ? 'auto' : 'none'
        }}
        onScroll={handleScroll}
      >
        <SubmittedVersionLayer kind={kind} previewUrl={previewUrl} rows={rows} xrayFilter={true} file={file} result={result} />
        {/* NOTE: Highlights are now embedded in the document itself from backend, not overlaid */}
      </div>
      
      {/* Center indicator showing X-ray analysis is active */}
      <div className="pointer-events-none absolute left-1/2 top-4 z-10 -translate-x-1/2 rounded-full bg-violet-600/95 px-4 py-1.5 text-xs font-bold text-white shadow-lg backdrop-blur-sm">
        <Eye className="mr-1.5 inline h-3.5 w-3.5" />
        X-ray Analysis Active
      </div>
      
      {/* Draggable slider */}
      <button
        type="button"
        role="slider"
        aria-label="X-ray comparison position"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(reveal)}
        title="Drag to reveal X-ray view"
        className="absolute inset-y-0 z-20 w-12 cursor-ew-resize touch-none outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
        style={{ left: `${reveal}%`, transform: 'translateX(-50%)' }}
        onPointerDown={(event) => {
          event.preventDefault();
          event.currentTarget.setPointerCapture(event.pointerId);
          updateRevealFromClientX(event.clientX);
        }}
        onPointerMove={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            updateRevealFromClientX(event.clientX);
          }
        }}
        onKeyDown={handleKeyDown}
      >
        <span className="absolute inset-y-0 left-1/2 w-1 -translate-x-1/2 bg-white shadow-[0_0_18px_rgba(255,255,255,0.95)]" />
        <span className="absolute left-1/2 top-1/2 flex h-12 w-12 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-white/80 bg-slate-950/85 text-white shadow-2xl">
          <MoveHorizontal className="h-5 w-5" />
        </span>
      </button>
    </div>
  );
}

function DocumentPreview({
  file,
  previewUrl,
  result,
  mode,
  showEvidenceMarkers,
}: {
  file: File | null;
  previewUrl: string | null;
  result: AnalysisResult | null;
  mode: 'document' | 'xray';
  showEvidenceMarkers: boolean;
}) {
  const rows = useMemo(
    () => (result?.extracted_text || '').split('\n').filter(Boolean).slice(0, 28),
    [result?.extracted_text]
  );
  const kind = friendlyType(file, result).toLowerCase();

  if (mode === 'xray' && result) {
    const recovered = result.recovered_version;
    const regions = buildVisualRegions(result);
    const previewHeight = 'h-[calc(100vh-205px)] min-h-[640px]';

    if (!file || !previewUrl) {
      return (
        <div className="flex h-full min-h-[520px] items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white text-center">
          <div>
            <Eye className="mx-auto mb-4 h-12 w-12 text-slate-300" />
            <p className="text-sm font-semibold text-slate-700">Upload a document to inspect it</p>
            <p className="mt-1 text-xs text-slate-400">PDF and image files are supported.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-violet-700">X-ray Signal</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{recovered.title}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-full bg-violet-100 px-3 py-1 text-xs font-bold text-violet-700">
                {Math.round((recovered.confidence || 0) * 100)}% confidence
              </span>
            </div>
          </div>

          <div className="bg-[#e7e5ed] p-4 lg:p-5">
            <div className="relative mx-auto w-full max-w-[1120px] overflow-hidden rounded-md bg-neutral-950 shadow-lg">
              <XrayComparison
                kind={kind}
                previewUrl={previewUrl}
                result={result}
                rows={rows}
                regions={regions}
                showEvidenceMarkers={showEvidenceMarkers}
                previewHeight={previewHeight}
                file={file}
              />
            </div>
          </div>
        </section>

        <section className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <div className="grid gap-0 lg:grid-cols-[1fr_1.15fr]">
            <div className="border-b border-slate-100 bg-slate-50 p-4 lg:border-b-0 lg:border-r">
              <p className="text-xs font-bold uppercase tracking-wide text-slate-500">How It Was Altered</p>
              <p className="mt-1 text-sm font-semibold text-slate-900">{recovered.method}</p>
              <p className="mt-3 text-sm leading-relaxed text-slate-600">{recovered.summary}</p>
              {result.ai_explanation?.likely_alteration && (
                <p className="mt-3 rounded-lg bg-violet-50 p-3 text-sm leading-relaxed text-violet-950">
                  {result.ai_explanation.likely_alteration}
                </p>
              )}
            </div>
            <div className="max-h-[320px] overflow-auto p-4">
              {recovered.changes.length > 0 ? (
                <div className="grid gap-3 md:grid-cols-2">
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
                <div className="flex h-56 items-center justify-center text-center text-sm text-slate-500">
                  <div>
                    <Eye className="mx-auto mb-3 h-8 w-8 text-slate-300" />
                    <p>No previous-version edits were recovered.</p>
                  </div>
                </div>
              )}
            </div>
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
          <p className="mt-1 text-xs text-slate-400">PDF and image files are supported.</p>
        </div>
      </div>
    );
  }

  if (kind === 'image') {
    return (
      <div className="relative h-full min-h-[520px] overflow-hidden rounded-lg border border-slate-200 bg-neutral-900">
        <img src={previewUrl} alt="Uploaded document" className="h-full w-full object-contain" />
        {/* Highlights are now embedded in the image from backend */}
      </div>
    );
  }

  if (kind === 'pdf') {
    return (
      <div className="relative h-full min-h-[620px] overflow-hidden rounded-lg border border-slate-200 bg-white">
        <PdfFrame title="PDF preview" previewUrl={previewUrl} className="min-h-[620px]" />
        {/* Highlights are now embedded in the PDF from backend */}
      </div>
    );
  }

function DocxPreview({ file, xrayFilter }: { file: File; xrayFilter?: boolean }) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  React.useEffect(() => {
    let active = true;
    const processFile = async () => {
      try {
        const buffer = await file.arrayBuffer();
        const mammoth = await import('mammoth');
        const result = await mammoth.convertToHtml({ 
          arrayBuffer: buffer,
          styleMap: [
            "p[style-name='Heading 1'] => h1:fresh",
            "p[style-name='Heading 2'] => h2:fresh",
            "p[style-name='Heading 3'] => h3:fresh",
            "b => strong",
            "i => em",
          ]
        });
        if (active) {
          setContent(result.value);
          setLoading(false);
          if (result.messages.length > 0) {
            console.warn('Mammoth conversion warnings:', result.messages);
          }
        }
      } catch (err) {
        console.error('Document preview error:', err);
        if (active) {
          setError(err instanceof Error ? err.message : 'Unknown error');
          setContent(`<div class="text-center mt-10 p-6">
            <p class="text-red-600 font-semibold mb-2">Error rendering preview</p>
            <p class="text-slate-500 text-sm">${err instanceof Error ? err.message : 'Failed to load document'}</p>
            <p class="text-slate-400 text-xs mt-2">Note: Word documents are converted to PDF for X-ray analysis</p>
          </div>`);
          setLoading(false);
        }
      }
    };
    processFile();
    return () => {
      active = false;
    };
  }, [file]);

  const filterStyle = xrayFilter
    ? { filter: 'invert(0.88) contrast(1.25) hue-rotate(180deg) saturate(0.3) brightness(1.1)' }
    : undefined;

  return (
    <div className="relative h-full w-full overflow-hidden bg-white" style={filterStyle}>
      <style>{`
        .doc-preview-container p { 
          margin-bottom: 0.75rem; 
          font-size: 14px; 
          line-height: 1.7;
          color: #1e293b;
          font-family: 'Segoe UI', system-ui, sans-serif;
        }
        .doc-preview-container h1 {
          font-size: 24px;
          font-weight: 700;
          margin: 1.5rem 0 1rem 0;
          color: #0f172a;
        }
        .doc-preview-container h2 {
          font-size: 20px;
          font-weight: 600;
          margin: 1.25rem 0 0.75rem 0;
          color: #1e293b;
        }
        .doc-preview-container h3 {
          font-size: 16px;
          font-weight: 600;
          margin: 1rem 0 0.5rem 0;
          color: #334155;
        }
        .doc-preview-container strong {
          font-weight: 600;
          color: #0f172a;
        }
        .doc-preview-container em {
          font-style: italic;
        }
        .doc-preview-container ul, .doc-preview-container ol {
          margin: 0.5rem 0 0.5rem 1.5rem;
          line-height: 1.7;
        }
        .doc-preview-container li {
          margin-bottom: 0.25rem;
        }
      `}</style>
      {loading ? (
        <div className="flex h-full items-center justify-center">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent mb-3"></div>
            <p className="text-sm font-semibold text-slate-600">Loading document preview...</p>
            <p className="text-xs text-slate-400 mt-2">Converting to PDF for analysis...</p>
          </div>
        </div>
      ) : (
        <div
          className="doc-preview-container h-full w-full overflow-auto p-6"
          dangerouslySetInnerHTML={{ __html: content }}
        />
      )}
    </div>
  );
}

  return (
    <div className="h-full min-h-[520px] overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="border-b border-slate-100 bg-slate-50 px-4 py-3">
        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Document Preview</p>
        <p className="mt-1 text-sm font-semibold text-slate-900">{file.name}</p>
      </div>
      <div className="h-[560px]">
        {kind === 'word' ? (
          <DocxPreview file={file} />
        ) : (
          <div className="h-full overflow-auto p-4">
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
                  <p>Run forensics to render extracted text and X-ray traces.</p>
                </div>
              </div>
            )}
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
  const [savingDecision, setSavingDecision] = useState<ReviewDecision | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [selectedSignalId, setSelectedSignalId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'document' | 'xray'>('document');
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState({
    autoOpenXray: true,
    showEvidenceMarkers: true,
  });
  const [reviewDecision, setReviewDecision] = useState<ReviewDecision | null>(null);
  const [decisionMessage, setDecisionMessage] = useState('');
  const [cerebrasApiKey, setCerebrasApiKey] = useState('');
  const [isApiKeyEntered, setIsApiKeyEntered] = useState(false);

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
    if (!isSupportedUpload(selected)) {
      event.target.value = '';
      alert('Only PDF and image files are supported. Word and Excel files are not accepted.');
      return;
    }
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(selected);
    setPreviewUrl(URL.createObjectURL(selected));
    setResult(null);
    setSelectedSignalId(null);
    setViewMode('document');
    setReviewDecision(null);
    setDecisionMessage('');
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setIsAnalyzing(true);
    setViewMode('document');
    const formData = new FormData();
    formData.append('file', file);
    if (cerebrasApiKey.trim()) {
      formData.append('cerebras_api_key', cerebrasApiKey.trim());
    }

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
      setReviewDecision(null);
      setDecisionMessage('');
      setSelectedSignalId(data.fraud_signals[0]?.id ?? null);
      
      // Fetch highlighted document if we have coordinates
      const coordinates = data.feature_summary?.highlight_coordinates;
      console.log('Highlight coordinates:', coordinates);
      
      if (coordinates && coordinates.length > 0) {
        console.log(`Found ${coordinates.length} highlight regions, fetching highlighted document...`);
        try {
          const highlightFormData = new FormData();
          highlightFormData.append('file', file);
          highlightFormData.append('highlight_regions', JSON.stringify(coordinates));
          
          const highlightResponse = await fetch(`${API_BASE_URL}/api/v1/highlighted-document`, {
            method: 'POST',
            body: highlightFormData,
          });
          
          if (highlightResponse.ok) {
            console.log('Successfully fetched highlighted document');
            const highlightedBlob = await highlightResponse.blob();
            
            // Revoke old preview URL
            if (previewUrl) {
              URL.revokeObjectURL(previewUrl);
            }
            
            // Create new URL from highlighted document
            const highlightedUrl = URL.createObjectURL(highlightedBlob);
            setPreviewUrl(highlightedUrl);
            console.log('Preview URL updated with highlighted document');
          } else {
            console.error('Failed to fetch highlighted document:', await highlightResponse.text());
          }
        } catch (error) {
          console.error('Failed to fetch highlighted document:', error);
          // Continue with original document if highlighting fails
        }
      } else {
        console.log('No highlight coordinates found in analysis result');
      }
      
      if (settings.autoOpenXray && data.recovered_version.available) {
        setViewMode('xray');
      }
    } catch (error) {
      console.error('Error analyzing document:', error);
      alert('Failed to analyze document. Make sure the backend is running and CORS is enabled.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleReviewDecision = async (decision: ReviewDecision) => {
    if (!file || !result) return;
    setSavingDecision(decision);
    setDecisionMessage('');

    const formData = new FormData();
    formData.append('decision', decision);
    formData.append('file', file);
    formData.append('analysis_json', JSON.stringify(result));

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/review-decision`, {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setReviewDecision(decision);
      setDecisionMessage(decision === 'accepted' ? 'Saved to authorized documents.' : 'Saved to private unauthorized documents.');
    } catch (error) {
      console.error('Error saving review decision:', error);
      alert('Failed to save the review decision. Make sure the backend is running.');
    } finally {
      setSavingDecision(null);
    }
  };

  const trustScore = result?.trust_score ?? 0;
  const riskLabel = !result ? 'Awaiting Scan' : trustScore >= 70 ? 'Low Risk' : trustScore >= 35 ? 'Review Required' : 'High Risk';
  const decisionLabel = reviewDecision === 'accepted' ? 'Accepted' : reviewDecision === 'rejected' ? 'Rejected' : 'Pending';

  return (
    <div className="min-h-screen bg-[#f8f6fb] text-slate-950">
      <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 bg-white px-5 py-2">
        <div className="flex min-w-0 items-center gap-3">
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
        {!isApiKeyEntered && (
          <label className="order-3 flex w-full min-w-[220px] items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus-within:border-violet-300 focus-within:bg-white md:order-none md:mx-4 md:w-auto md:max-w-[430px] md:flex-1">
            <Bot className="h-4 w-4 shrink-0 text-violet-600" />
            <input
              type="password"
              value={cerebrasApiKey}
              onChange={(event) => setCerebrasApiKey(event.target.value)}
              onBlur={() => {
                if (cerebrasApiKey.trim().length > 0) {
                  setIsApiKeyEntered(true);
                }
              }}
              placeholder="OpenRouter API key for descriptions"
              aria-label="OpenRouter API key"
              autoComplete="off"
              className="min-w-0 flex-1 bg-transparent text-sm font-semibold text-slate-700 outline-none placeholder:text-slate-400"
            />
          </label>
        )}
        <div className="flex items-center gap-2">
          {reviewDecision && (
            <span
              className={cx(
                'hidden rounded-full px-3 py-1 text-xs font-black uppercase tracking-wide sm:inline-flex',
                reviewDecision === 'accepted' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
              )}
            >
              {decisionLabel}
            </span>
          )}
          <button
            onClick={() => setSettingsOpen(true)}
            className="hidden rounded-lg border border-slate-200 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 sm:flex"
            type="button"
            aria-expanded={settingsOpen}
          >
            <Settings className="mr-2 h-4 w-4" />
            Settings
          </button>
          <button
            onClick={() => handleReviewDecision('rejected')}
            disabled={!result || savingDecision !== null}
            className={cx(
              'rounded-lg border px-3 py-2 text-sm font-bold transition-colors',
              !result || savingDecision !== null
                ? 'cursor-not-allowed border-slate-200 bg-slate-100 text-slate-400'
                : reviewDecision === 'rejected'
                  ? 'border-red-200 bg-red-50 text-red-700'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
            )}
            type="button"
          >
            {savingDecision === 'rejected' ? <Activity className="mr-2 inline h-4 w-4 animate-spin" /> : <XCircle className="mr-2 inline h-4 w-4" />}
            {savingDecision === 'rejected' ? 'Saving' : 'Reject'}
          </button>
          <button
            onClick={() => handleReviewDecision('accepted')}
            disabled={!result || savingDecision !== null}
            className={cx(
              'rounded-lg px-3 py-2 text-sm font-bold text-white transition-colors',
              !result || savingDecision !== null
                ? 'cursor-not-allowed bg-slate-300'
                : reviewDecision === 'accepted'
                  ? 'bg-emerald-600 hover:bg-emerald-700'
                  : 'bg-slate-900 hover:bg-slate-800'
            )}
            type="button"
          >
            {savingDecision === 'accepted' ? <Activity className="mr-2 inline h-4 w-4 animate-spin" /> : <Check className="mr-2 inline h-4 w-4" />}
            {savingDecision === 'accepted' ? 'Saving' : 'Accept'}
          </button>
        </div>
      </header>

      {settingsOpen && (
        <div className="fixed inset-0 z-50">
          <button
            type="button"
            aria-label="Close settings"
            className="absolute inset-0 bg-slate-950/20"
            onClick={() => setSettingsOpen(false)}
          />
          <section className="absolute right-5 top-16 w-[min(360px,calc(100vw-40px))] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
              <div>
                <p className="text-sm font-black text-slate-900">Settings</p>
                <p className="text-xs text-slate-500">Review controls</p>
              </div>
              <button
                type="button"
                aria-label="Close settings"
                className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
                onClick={() => setSettingsOpen(false)}
              >
                <XCircle className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-3 p-4">
              <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-slate-200 p-3">
                <span className="text-sm font-bold text-slate-800">Open X-ray automatically</span>
                <input
                  type="checkbox"
                  checked={settings.autoOpenXray}
                  onChange={(event) => setSettings((current) => ({ ...current, autoOpenXray: event.target.checked }))}
                  className="h-4 w-4 accent-violet-700"
                />
              </label>
              <label className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-slate-200 p-3">
                <span className="text-sm font-bold text-slate-800">Show red evidence marks</span>
                <input
                  type="checkbox"
                  checked={settings.showEvidenceMarkers}
                  onChange={(event) => setSettings((current) => ({ ...current, showEvidenceMarkers: event.target.checked }))}
                  className="h-4 w-4 accent-violet-700"
                />
              </label>
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase text-slate-400">Backend</p>
                <p className="mt-1 break-all text-sm font-semibold text-slate-700">{API_BASE_URL}</p>
              </div>
            </div>
          </section>
        </div>
      )}

      <main className="grid min-h-[calc(100vh-96px)] grid-cols-1 xl:grid-cols-[280px_1fr_390px]">
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
              <div>
                <p className="text-xs font-semibold text-slate-400">Decision</p>
                <p
                  className={cx(
                    'font-bold',
                    reviewDecision === 'accepted' && 'text-emerald-700',
                    reviewDecision === 'rejected' && 'text-red-700',
                    !reviewDecision && 'text-slate-800'
                  )}
                >
                  {decisionLabel}
                </p>
                {decisionMessage && <p className="mt-1 text-xs font-semibold text-slate-500">{decisionMessage}</p>}
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
              <p className="mt-1 text-xs text-slate-400">PDF and Image files only</p>
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
          <DocumentPreview
            file={file}
            previewUrl={previewUrl}
            result={result}
            mode={viewMode}
            showEvidenceMarkers={settings.showEvidenceMarkers}
          />
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
                Enter a Cerebras API key at the top to generate descriptions, or run without one for local fallback text.
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
                  setReviewDecision(null);
                  setDecisionMessage('');
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
