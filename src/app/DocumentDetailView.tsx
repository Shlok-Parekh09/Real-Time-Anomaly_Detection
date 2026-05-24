import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ChevronDown,
  FileText,
  Minus,
  Plus,
  Upload,
  X,
} from 'lucide-react';
import axios from 'axios';
import * as pdfjsLib from 'pdfjs-dist';
import type { BookEntry } from './BooksListView';

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url,
).toString();

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

/* ─── Types ────────────────────────────────────────────────────────────── */

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

interface HighlightRegion {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
  label?: string;
  severity?: string;
  signal_id?: string;
}

interface DocumentDetailViewProps {
  book: BookEntry;
  onBack: () => void;
}

/* ─── Helpers ──────────────────────────────────────────────────────────── */

function cx(...classes: Array<string | false | null | undefined>) {
  return classes.filter(Boolean).join(' ');
}

function timeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `about ${minutes} minute${minutes > 1 ? 's' : ''} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `about ${hours} hour${hours > 1 ? 's' : ''} ago`;
  const days = Math.floor(hours / 24);
  return `about ${days} day${days > 1 ? 's' : ''} ago`;
}

function severityColor(severity: string) {
  if (severity === 'high') return { border: '#ff4d6a', bg: '#ff4d6a', light: '#fff0f3' };
  if (severity === 'medium') return { border: '#ff9f43', bg: '#ff9f43', light: '#fff8f0' };
  return { border: '#94a3b8', bg: '#94a3b8', light: '#f8fafc' };
}

/* ─── Signal Card Component (matching reference image) ─────────────────── */

function SignalCard({ signal, defaultOpen }: { signal: FraudSignal; defaultOpen: boolean }) {
  const [expanded, setExpanded] = useState(defaultOpen);
  const colors = severityColor(signal.severity);

  return (
    <div
      style={{ borderColor: colors.border, borderWidth: '1.5px' }}
      className="rounded-2xl bg-white overflow-hidden transition-all duration-200"
    >
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 px-4 py-3.5 text-left"
        style={{ backgroundColor: expanded ? colors.light : 'white' }}
      >
        {/* Red/orange circle badge */}
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-white text-sm font-black"
          style={{ backgroundColor: colors.bg }}
        >
          !
        </div>

        {/* Signal name */}
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-bold text-slate-900">{signal.name}</p>
        </div>

        {/* Expand/collapse */}
        <div className="shrink-0 text-slate-400">
          {expanded ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        </div>
      </button>

      {/* Body — collapsible */}
      {expanded && (
        <div className="px-4 pb-4 pt-1" style={{ backgroundColor: colors.light }}>
          {/* Summary line */}
          <p className="text-xs leading-relaxed text-slate-700 mb-2">{signal.summary}</p>

          {/* Full description */}
          {signal.description && signal.description !== signal.summary && (
            <p className="text-[11px] leading-relaxed text-slate-500 mb-3">{signal.description}</p>
          )}

          {/* Evidence list / table */}
          {signal.evidence.length > 0 && (
            <div className="space-y-1.5 mt-3">
              {(() => {
                const isTable = signal.evidence[0]?.startsWith('table:');
                if (isTable) {
                  const headers = signal.evidence[0].replace('table:', '').split('|');
                  const rows = signal.evidence.slice(1).map(r => r.split('|'));
                  
                  return (
                    <div className="w-full">
                      <table className="w-full text-left border-y border-slate-200">
                        <thead>
                          <tr>
                            {headers.map((h, i) => (
                              <th key={i} className="py-2 px-1 text-[10px] font-bold text-slate-800 uppercase tracking-wider border-b border-slate-200">
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((row, rIdx) => (
                            <tr key={rIdx} className="border-b border-slate-100 last:border-0">
                              {row.map((cell, cIdx) => (
                                <td key={cIdx} className="py-2 px-1 text-[11px] font-medium text-slate-600">
                                  {cell}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  );
                }

                // Standard bullet list for non-table evidence
                return signal.evidence.map((ev, i) => (
                  <div key={`ev-${i}`} className="flex items-start gap-2">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: colors.bg }} />
                    <span className="text-[11px] leading-snug text-slate-600 font-medium">{ev}</span>
                  </div>
                ));
              })()}
            </div>
          )}

          {/* Confidence bar */}
          <div className="mt-3 flex items-center gap-2">
            <span className="text-[9px] font-bold uppercase tracking-widest text-slate-400">Confidence</span>
            <div className="h-1.5 flex-1 rounded-full bg-white/70 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${signal.confidence * 100}%`, backgroundColor: colors.bg }}
              />
            </div>
            <span className="text-[10px] font-bold text-slate-500">{Math.round(signal.confidence * 100)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── PDF Page Thumbnail (real rendered preview) ───────────────────────── */

function PdfPageThumbnail({
  pdfUrl,
  pageNum,
  isActive,
  onClick,
}: {
  pdfUrl: string;
  pageNum: number;
  isActive: boolean;
  onClick: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [rendered, setRendered] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const renderPage = async () => {
      try {
        const pdf = await pdfjsLib.getDocument(pdfUrl).promise;
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale: 0.3 });

        const canvas = canvasRef.current;
        if (!canvas || cancelled) return;

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        await page.render({ canvasContext: ctx, viewport }).promise;
        if (!cancelled) setRendered(true);
      } catch (err) {
        // Silently fail — show fallback icon
      }
    };

    renderPage();
    return () => { cancelled = true; };
  }, [pdfUrl, pageNum]);

  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'relative w-full rounded-xl border-2 overflow-hidden transition-all bg-white',
        isActive
          ? 'border-[#6366f1] ring-[3px] ring-[#6366f1]/25 shadow-lg'
          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm',
      )}
    >
      <div className="w-full bg-white flex items-center justify-center min-h-[90px]">
        <canvas
          ref={canvasRef}
          className={cx('w-full', rendered ? 'block' : 'hidden')}
        />
        {!rendered && (
          <div className="flex flex-col items-center gap-1 py-5">
            <FileText className="h-7 w-7 text-slate-200" />
          </div>
        )}
      </div>
      <div className={cx(
        'w-full py-1 text-center text-[11px] font-bold text-white',
        isActive ? 'bg-[#6366f1]' : 'bg-[#64748b]',
      )}>
        {pageNum}
      </div>
    </button>
  );
}

/* ─── Image Thumbnail (fallback for non-PDF) ───────────────────────────── */

function ImageThumbnail({
  previewUrl,
  pageNum,
  isActive,
  onClick,
}: {
  previewUrl: string;
  pageNum: number;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cx(
        'relative w-full rounded-xl border-2 overflow-hidden transition-all bg-white',
        isActive
          ? 'border-[#6366f1] ring-[3px] ring-[#6366f1]/25 shadow-lg'
          : 'border-slate-200 hover:border-slate-300 hover:shadow-sm',
      )}
    >
      <div className="w-full bg-white p-1">
        <img src={previewUrl} alt={`Page ${pageNum}`} className="w-full object-contain" />
      </div>
      <div className={cx(
        'w-full py-1 text-center text-[11px] font-bold text-white',
        isActive ? 'bg-[#6366f1]' : 'bg-[#64748b]',
      )}>
        {pageNum}
      </div>
    </button>
  );
}

/* ─── Main Component ───────────────────────────────────────────────────── */

export default function DocumentDetailView({ book, onBack }: DocumentDetailViewProps) {
  const [activeTab, setActiveTab] = useState<'capture' | 'detect'>('detect');
  const [showSignals, setShowSignals] = useState(true);
  const [activePage, setActivePage] = useState(1);
  const [highlightedDocUrl, setHighlightedDocUrl] = useState<string | null>(null);

  const result = book.analysisResult;
  const signals: FraudSignal[] = result?.fraud_signals ?? [];
  const pageCount = result?.metadata?.page_count || 1;
  const fileType = result?.file_type || 'pdf';

  const highlightRegions: HighlightRegion[] = useMemo(() => {
    const coords = result?.feature_summary?.highlight_coordinates;
    if (Array.isArray(coords)) return coords;
    return [];
  }, [result]);

  const highCount = useMemo(() => signals.filter((s) => s.severity === 'high').length, [signals]);
  const mediumCount = useMemo(() => signals.filter((s) => s.severity === 'medium').length, [signals]);
  const lowCount = useMemo(() => signals.filter((s) => s.severity === 'low').length, [signals]);
  const totalSignals = signals.length;

  // Fetch highlighted document from backend
  useEffect(() => {
    if (!book.file || highlightRegions.length === 0) return;

    let blobUrl: string | null = null;

    const fetchHighlighted = async () => {
      try {
        const formData = new FormData();
        formData.append('file', book.file);
        formData.append('highlight_regions', JSON.stringify(highlightRegions));

        const response = await axios.post(`${API_BASE_URL}/api/v1/highlighted-document`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
          responseType: 'blob',
        });

        blobUrl = URL.createObjectURL(response.data);
        setHighlightedDocUrl(blobUrl);
      } catch (err) {
        console.error('Failed to load highlighted document', err);
      }
    };

    fetchHighlighted();

    return () => {
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
  }, [book.file, highlightRegions]);

  const displayUrl = highlightedDocUrl || book.previewUrl;

  const handleReviewDecision = async (decision: 'accepted' | 'rejected') => {
    if (!book.file || !result) return;
    try {
      const formData = new FormData();
      formData.append('decision', decision);
      formData.append('file', book.file);
      formData.append('analysis_json', JSON.stringify(result));
      await axios.post(`${API_BASE_URL}/api/v1/review-decision`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      alert(`Document successfully ${decision}!`);
      onBack();
    } catch (err) {
      console.error('Failed to submit review decision', err);
      alert('Failed to submit decision.');
    }
  };

  return (
    <div className="flex h-screen flex-col bg-white" style={{ fontFamily: "'Inter', system-ui, -apple-system, sans-serif" }}>
      {/* ─── Top Header Bar (matching reference image) ───────────────── */}
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-5">
        <div className="flex items-center gap-3 min-w-0">
          <button
            onClick={onBack}
            className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-slate-500 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <h1 className="truncate text-sm font-extrabold text-slate-900">{book.name}</h1>
        </div>

        {/* Stats */}
        <div className="hidden lg:flex items-center gap-8 text-xs text-slate-500">
          <div className="flex flex-col">
            <span className="font-bold text-slate-700">Uploads</span>
            <span>1</span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-slate-700">Documents</span>
            <span>1</span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-slate-700">Created</span>
            <span>{timeAgo(book.createdAt)}</span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-slate-700">Modified</span>
            <span>{timeAgo(book.dateModified)}</span>
          </div>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-2">
          <button className="hidden sm:flex items-center gap-1.5 rounded-lg border border-slate-200 px-4 py-2 text-[11px] font-bold text-slate-600 hover:bg-slate-50 transition-colors uppercase tracking-wide">
            Financial Analysis
          </button>
          <button className="flex items-center gap-1.5 rounded-lg bg-[#6366f1] px-4 py-2 text-[11px] font-bold text-white uppercase tracking-wide shadow-md shadow-indigo-200 transition-all hover:bg-[#4f46e5]">
            <Upload className="h-3.5 w-3.5" />
            Upload
            <ChevronDown className="h-3 w-3 ml-0.5" />
          </button>
        </div>
      </header>

      {/* ─── Document Info Sub-header ────────────────────────────────── */}
      <div className="flex shrink-0 items-center gap-8 border-b border-slate-100 bg-white px-5 py-2 text-xs">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Document Type</span>
          <p className="text-xs font-bold text-slate-800 mt-0.5">
            {fileType === 'pdf' ? 'Bank statement' : fileType === 'image' ? 'Image document' : 'Document'}
          </p>
        </div>
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Verified Date</span>
          <p className="text-xs font-bold text-slate-800 mt-0.5">{book.dateModified.toLocaleDateString('en-GB')}</p>
        </div>
      </div>

      {/* ─── Main 3-column layout ────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — Page thumbnails with real previews */}
        <aside className="w-[110px] shrink-0 overflow-y-auto border-r border-slate-200 bg-[#f1f0f6] p-2.5 space-y-3">
          {Array.from({ length: pageCount }, (_, i) => i + 1).map((num) => (
            fileType === 'pdf' ? (
              <PdfPageThumbnail
                key={num}
                pdfUrl={book.previewUrl}
                pageNum={num}
                isActive={activePage === num}
                onClick={() => setActivePage(num)}
              />
            ) : (
              <ImageThumbnail
                key={num}
                previewUrl={book.previewUrl}
                pageNum={num}
                isActive={activePage === num}
                onClick={() => setActivePage(num)}
              />
            )
          ))}
        </aside>

        {/* Center — Document viewer */}
        <main className="relative flex-1 overflow-auto bg-[#e5e2ed] flex justify-center p-5">
          <div className="w-full max-w-[950px] h-full">
            <div className="bg-white rounded shadow-2xl w-full h-full overflow-hidden relative">
              {fileType === 'image' ? (
                <div className="flex h-full items-center justify-center overflow-auto p-4">
                  <img
                    src={displayUrl}
                    alt={book.name}
                    className="max-h-full max-w-full object-contain"
                  />
                </div>
              ) : fileType === 'pdf' ? (
                <iframe
                  title="PDF preview"
                  src={`${displayUrl}#view=FitH&toolbar=0&navpanes=0&scrollbar=1&page=${activePage}`}
                  className="h-full w-full border-0"
                />
              ) : (
                <div className="h-full overflow-auto p-8">
                  <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-slate-700">
                    {result?.extracted_text || 'No preview available for this file type.'}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </main>

        {/* Right sidebar — Detect Signals panel */}
        {showSignals && (
          <aside className="w-[380px] shrink-0 flex flex-col border-l border-slate-200 bg-white">
            {/* Panel header */}
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowSignals(false)}
                  className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
                <h2 className="text-sm font-extrabold text-slate-900">Detect Signals</h2>
              </div>

              {/* CAPTURE / DETECT tabs */}
              <div className="flex items-center rounded-full bg-slate-100 p-0.5">
                <button
                  type="button"
                  onClick={() => setActiveTab('capture')}
                  className={cx(
                    'rounded-full px-3.5 py-1.5 text-[10px] font-bold transition-all uppercase tracking-wider',
                    activeTab === 'capture'
                      ? 'bg-white text-slate-800 shadow-sm'
                      : 'text-slate-400 hover:text-slate-600',
                  )}
                >
                  Capture
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('detect')}
                  className={cx(
                    'rounded-full px-3.5 py-1.5 text-[10px] font-bold transition-all uppercase tracking-wider',
                    activeTab === 'detect'
                      ? 'bg-white text-slate-800 shadow-sm'
                      : 'text-slate-400 hover:text-slate-600',
                  )}
                >
                  Detect
                </button>
              </div>
            </div>

            {/* Signals list */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {activeTab === 'detect' ? (
                signals.length > 0 ? (
                  <>
                    {/* Summary banner */}
                    <div className="rounded-2xl bg-[#fff0f3] border border-[#ffd6de] px-4 py-3">
                      <div className="flex items-center gap-2 mb-0.5">
                        <AlertTriangle className="h-4 w-4 text-[#ff4d6a]" />
                        <span className="text-sm font-bold text-[#ff4d6a]">
                          {totalSignals} Signal{totalSignals !== 1 ? 's' : ''} Detected
                        </span>
                      </div>
                      <p className="text-[11px] font-medium text-slate-500 ml-6">
                        {highCount > 0 && `${highCount} high severity`}
                        {highCount > 0 && mediumCount > 0 && ', '}
                        {mediumCount > 0 && `${mediumCount} medium severity`}
                        {(highCount > 0 || mediumCount > 0) && lowCount > 0 && ', '}
                        {lowCount > 0 && `${lowCount} low severity`}
                      </p>
                    </div>

                    {/* Signal cards */}
                    {signals.map((signal, i) => (
                      <SignalCard
                        key={`${signal.id}-${i}`}
                        signal={signal}
                        defaultOpen={i === 0}
                      />
                    ))}
                  </>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-16 text-center">
                    <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100">
                      <svg className="h-7 w-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <p className="text-sm font-bold text-slate-700">No fraud signals detected</p>
                    <p className="text-xs text-slate-400 max-w-[220px]">The document passed all forensic checks.</p>
                  </div>
                )
              ) : (
                /* CAPTURE tab — metadata */
                <div className="space-y-2">
                  <p className="text-xs font-bold text-slate-600 mb-3">Document Metadata</p>
                  {result?.metadata &&
                    Object.entries(result.metadata)
                      .filter(([_, v]) => v !== null && v !== undefined && v !== '' && !Array.isArray(v))
                      .slice(0, 15)
                      .map(([key, value]) => (
                        <div key={key} className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2.5 border border-slate-100">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-[11px] font-semibold text-slate-700 text-right break-all">
                            {String(value)}
                          </span>
                        </div>
                      ))}
                </div>
              )}
            </div>

            {/* AI analysis footer */}
            {result?.ai_explanation && activeTab === 'detect' && (
              <div className="border-t border-slate-100 px-4 py-3.5 bg-[#fafafa]">
                <p className="text-[10px] font-extrabold text-indigo-600 uppercase tracking-wider mb-1.5">
                  AI Analysis
                </p>
                <p className="text-[11px] leading-relaxed text-slate-600">
                  {result.ai_explanation.summary}
                </p>
                {result.ai_explanation.recommended_action && (
                  <p className="mt-2 text-[11px] text-slate-600">
                    <span className="font-bold text-slate-800">Action:</span>{' '}
                    {result.ai_explanation.recommended_action}
                  </p>
                )}
              </div>
            )}

            {/* Approve / Reject Actions */}
            {activeTab === 'detect' && (
              <div className="flex gap-2 p-4 border-t border-slate-200 bg-white mt-auto shrink-0">
                <button
                  onClick={() => handleReviewDecision('rejected')}
                  className="flex-1 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-[11px] font-bold text-red-700 uppercase tracking-wider hover:bg-red-100 transition-colors"
                >
                  Reject
                </button>
                <button
                  onClick={() => handleReviewDecision('accepted')}
                  className="flex-1 rounded-lg border border-transparent bg-emerald-500 px-4 py-2.5 text-[11px] font-bold text-white uppercase tracking-wider hover:bg-emerald-600 shadow-sm transition-colors"
                >
                  Approve
                </button>
              </div>
            )}
          </aside>
        )}

        {/* Toggle button when signals panel is closed */}
        {!showSignals && (
          <button
            onClick={() => setShowSignals(true)}
            className="absolute right-0 top-1/2 -translate-y-1/2 z-30 flex items-center gap-1.5 rounded-l-xl bg-[#ff4d6a] px-2.5 py-4 text-white shadow-lg hover:bg-[#e6445f] transition-colors"
          >
            <AlertTriangle className="h-5 w-5" />
            <span className="text-[10px] font-bold">{totalSignals}</span>
          </button>
        )}
      </div>
    </div>
  );
}
