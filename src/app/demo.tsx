import React, { useState, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Cell, Tooltip } from 'recharts';
import { CheckCircle, AlertTriangle, XCircle, ChevronDown, ChevronUp, Clock, User, Building, FileText, ArrowRight, RotateCcw, Upload } from 'lucide-react';
import { AUTHENTIC_DATA, THRESHOLD, MEANS, N_SAMPLES, analyzeDoc } from './knn';

function cx(...c: (string | boolean | undefined)[]) { return c.filter(Boolean).join(' '); }

const CASE = {
  id: 'FRD-2024-00847', officer: 'Sarah Chen',
  branch: 'Mumbai Corporate Branch', property: '14B Nariman Point, Mumbai',
  loan: '₹ 2,40,00,000', docType: 'Land Title Deed + Income Certificate',
};

function Slider({ label, hint, value, onChange }: { label: string; hint: string; value: number; onChange: (v: number) => void }) {
  const pct = value;
  const color = pct > 85 || pct < 35 ? '#ef4444' : pct > 65 ? '#22c55e' : '#f59e0b';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between">
        <label className="text-sm font-semibold text-gray-700">{label}</label>
        <span className="text-sm font-bold tabular-nums" style={{ color }}>{value}</span>
      </div>
      <div className="relative">
        <input type="range" min={0} max={100} step={1} value={value}
          onChange={e => onChange(Number(e.target.value))}
          className="w-full h-2 rounded-full appearance-none cursor-pointer"
          style={{ background: `linear-gradient(to right, ${color} ${pct}%, #e5e7eb ${pct}%)` }} />
      </div>
      <p className="text-xs text-gray-400">{hint}</p>
    </div>
  );
}

function ProcessingStep({ label, done, active }: { label: string; done: boolean; active: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className={cx('w-5 h-5 rounded-full flex items-center justify-center shrink-0 text-xs font-bold transition-all',
        done ? 'bg-green-500 text-white' : active ? 'bg-blue-600 text-white animate-pulse' : 'bg-gray-200 text-gray-400')}>
        {done ? '✓' : ''}
      </div>
      <span className={cx('text-sm transition-colors', done ? 'text-gray-800 font-medium' : active ? 'text-blue-700 font-semibold' : 'text-gray-400')}>{label}</span>
      {active && <div className="ml-auto w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />}
    </div>
  );
}

function ScenarioBtn({ label, active, onClick }: { label: string; active?: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={cx('px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all',
        active ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300 hover:text-blue-600')}>
      {label}
    </button>
  );
}

function MetricPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4">
      <p className="text-xs text-gray-400 font-medium mb-1">{label}</p>
      <p className={cx('text-xl font-black', color)}>{value}</p>
    </div>
  );
}

function FindingCard({ n, title, plain, technical, severity }: { n: number; title: string; plain: string; technical: string; severity: string }) {
  const [open, setOpen] = useState(false);
  const cfg = { high: { bg: 'bg-red-50 border-red-200', badge: 'bg-red-100 text-red-700', icon: <XCircle className="w-4 h-4 text-red-500" /> },
    medium: { bg: 'bg-amber-50 border-amber-200', badge: 'bg-amber-100 text-amber-700', icon: <AlertTriangle className="w-4 h-4 text-amber-500" /> },
    low: { bg: 'bg-gray-50 border-gray-200', badge: 'bg-gray-100 text-gray-600', icon: <AlertTriangle className="w-4 h-4 text-gray-400" /> } }[severity] ?? { bg: 'bg-gray-50 border-gray-200', badge: 'bg-gray-100 text-gray-600', icon: null };
  return (
    <div className={cx('border rounded-xl overflow-hidden', cfg.bg)}>
      <button className="w-full text-left p-4 flex items-start gap-3" onClick={() => setOpen(o => !o)}>
        <div className="mt-0.5">{cfg.icon}</div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs text-gray-400 font-mono">Finding #{String(n).padStart(2,'0')}</span>
            <span className={cx('text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider', cfg.badge)}>{severity}</span>
          </div>
          <p className="text-sm font-semibold text-gray-800">{title}</p>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">{plain}</p>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400 shrink-0 mt-1" /> : <ChevronDown className="w-4 h-4 text-gray-400 shrink-0 mt-1" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} className="overflow-hidden">
            <div className="px-4 pb-4 pt-1 border-t border-black/5">
              <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-1">Technical Detail</p>
              <p className="text-xs font-mono text-gray-500 leading-relaxed">{technical}</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function RiskBadge({ score, tier }: { score: number; tier: 'green' | 'yellow' | 'red' }) {
  const cfg = {
    green: { bg: 'bg-green-50 border-green-200', num: 'text-green-600', label: 'Auto-Cleared', sub: 'No significant anomalies found.', Icon: CheckCircle, ic: 'text-green-500' },
    yellow: { bg: 'bg-amber-50 border-amber-200', num: 'text-amber-600', label: 'Review Required', sub: 'Minor anomalies detected. Assign to senior underwriter.', Icon: AlertTriangle, ic: 'text-amber-500' },
    red: { bg: 'bg-red-50 border-red-200', num: 'text-red-600', label: 'High Risk — Escalate', sub: 'High probability of forgery. Do not process. Alert FIU.', Icon: XCircle, ic: 'text-red-500' },
  }[tier];
  return (
    <div className={cx('border-2 rounded-2xl p-5 flex items-center gap-5', cfg.bg)}>
      <div className="text-center">
        <div className={cx('text-5xl font-black leading-none', cfg.num)}>{score}</div>
        <div className="text-xs text-gray-400 font-medium mt-1">Risk Score / 100</div>
      </div>
      <div className="w-px h-12 bg-black/10" />
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <cfg.Icon className={cx('w-5 h-5', cfg.ic)} />
          <span className={cx('text-lg font-black', cfg.num)}>{cfg.label}</span>
        </div>
        <p className="text-sm text-gray-600">{cfg.sub}</p>
        <p className="text-xs text-gray-400 mt-1 font-mono">Case {CASE.id} · Processed in 118ms</p>
      </div>
    </div>
  );
}

function ChartTip({ active, payload }: { active?: boolean; payload?: { payload: { x: number; y: number; type: string } }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 text-xs shadow-lg">
      <p className="text-gray-500">Metadata: <strong>{d.x.toFixed(1)}</strong></p>
      <p className="text-gray-500">Layout: <strong>{d.y.toFixed(1)}</strong></p>
      <p className={cx('font-semibold mt-1', d.type === 'current' ? 'text-blue-600' : 'text-green-600')}>
        {d.type === 'current' ? 'Submitted Document' : 'Baseline Record'}
      </p>
    </div>
  );
}

export function LiveDemoSection() {
  const [meta, setMeta] = useState(75);
  const [lay, setLay]   = useState(80);
  const [fnt, setFnt]   = useState(70);
  const [phase, setPhase] = useState<'idle' | 'processing' | 'done'>('idle');
  const [step, setStep]   = useState(0);

  const result = useMemo(() => analyzeDoc({ metadata: meta, layout: lay, font: fnt }), [meta, lay, fnt]);
  const tc = { green: '#22c55e', yellow: '#f59e0b', red: '#ef4444' }[result.tier];

  const chartData = useMemo(() => [
    ...AUTHENTIC_DATA.map(p => ({ x: p.metadata, y: p.layout, type: 'authentic' })),
    { x: meta, y: lay, type: 'current' },
  ], [meta, lay]);

  const STEPS = ['Extracting EXIF metadata & timestamps', 'Running Error Level Analysis (pixel)', 'Checking structural & font consistency', 'Querying FAISS index against baseline', 'Generating explainable AI narrative'];

  const handleSubmit = useCallback(() => {
    setPhase('processing'); setStep(0);
    STEPS.forEach((_, i) => setTimeout(() => setStep(i + 1), 500 * (i + 1)));
    setTimeout(() => setPhase('done'), 500 * (STEPS.length + 1));
  }, []);

  const scenarios: [string, number, number, number][] = [
    ['Authentic Sample', 75, 80, 70],
    ['Poor Scan Quality', 65, 55, 62],
    ['Suspected Forgery', 22, 38, 94],
  ];

  return (
    <section id="demo" className="bg-gray-50 py-16 px-4 border-t border-gray-200">
      <div className="max-w-5xl mx-auto">

        {/* Section label */}
        <div className="text-center mb-10">
          <span className="inline-block text-xs font-bold text-blue-600 uppercase tracking-widest bg-blue-50 border border-blue-100 px-3 py-1 rounded-full mb-3">Underwriter Workstation</span>
          <h2 className="text-3xl font-black text-gray-900 mb-2">Forensic Analysis Console</h2>
          <p className="text-gray-500 text-sm max-w-xl mx-auto">This is what the loan officer sees when a document comes in for review. Submit a document and watch the engine work.</p>
        </div>

        {/* Case file card */}
        <div className="bg-white border border-gray-200 rounded-2xl shadow-sm overflow-hidden mb-6">
          <div className="bg-gray-800 px-5 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-bold text-white">Active Case File</span>
              <span className="text-xs font-mono text-gray-400 bg-gray-700 px-2 py-0.5 rounded">{CASE.id}</span>
            </div>
            <span className={cx('text-[11px] font-bold px-2.5 py-1 rounded-full',
              phase === 'idle' ? 'bg-gray-600 text-gray-300' :
              phase === 'processing' ? 'bg-amber-500/20 text-amber-300' :
              'bg-green-500/20 text-green-300')}>
              {phase === 'idle' ? 'Awaiting Submission' : phase === 'processing' ? '⏳ Analyzing' : '✓ Report Ready'}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-px bg-gray-100">
            {[[User, 'Loan Officer', CASE.officer], [Building, 'Branch', CASE.branch],
              [FileText, 'Document Type', CASE.docType], [null, 'Property', CASE.property],
              [null, 'Loan Amount', CASE.loan], [Clock, 'Received', new Date().toLocaleTimeString('en-IN')]
            ].map(([Icon, label, val], i) => (
              <div key={i} className="bg-white px-4 py-3">
                <p className="text-[10px] text-gray-400 uppercase font-bold tracking-wider mb-0.5">{label as string}</p>
                <p className="text-sm text-gray-800 font-semibold">{val as string}</p>
              </div>
            ))}
          </div>
        </div>

        <AnimatePresence mode="wait">
          {phase === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-5">

              {/* Upload zone */}
              <div className="bg-white border-2 border-dashed border-gray-200 hover:border-blue-300 rounded-2xl p-10 text-center cursor-pointer transition-all group" onClick={handleSubmit}>
                <Upload className="w-10 h-10 text-gray-300 group-hover:text-blue-400 mx-auto mb-3 transition-colors" />
                <p className="text-base font-semibold text-gray-700 mb-1">Drop the document here, or <span className="text-blue-600">browse files</span></p>
                <p className="text-sm text-gray-400">PDF, JPG, PNG · Max 50MB · Encrypted in transit</p>
              </div>

              {/* Feature controls */}
              <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-6">
                <div className="flex items-center justify-between mb-5">
                  <div>
                    <h3 className="text-sm font-bold text-gray-800">Forensic Feature Preview</h3>
                    <p className="text-xs text-gray-400 mt-0.5">Simulates extracted feature scores. Adjust to test different document scenarios.</p>
                  </div>
                  <div className="flex gap-2 flex-wrap justify-end">
                    {scenarios.map(([label, m, l, f]) => (
                      <ScenarioBtn key={label} label={label}
                        active={meta === m && lay === l && fnt === f}
                        onClick={() => { setMeta(m); setLay(l); setFnt(f); }} />
                    ))}
                  </div>
                </div>
                <div className="grid md:grid-cols-3 gap-6 mb-6">
                  <Slider label="Metadata Consistency" hint="EXIF fields, timestamps, software signatures" value={meta} onChange={setMeta} />
                  <Slider label="Layout & Structure" hint="Margins, column alignment, bounding boxes" value={lay} onChange={setLay} />
                  <Slider label="Font & Pixel Variance" hint="Kerning, ELA compression artifacts" value={fnt} onChange={setFnt} />
                </div>
                <button onClick={handleSubmit}
                  className="w-full py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm transition-colors flex items-center justify-center gap-2 shadow-md shadow-blue-600/20">
                  Run Forensic Analysis <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </motion.div>
          )}

          {phase === 'processing' && (
            <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="bg-white border border-gray-200 rounded-2xl shadow-sm p-8 space-y-4">
              <div className="text-center mb-6">
                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <h3 className="text-lg font-bold text-gray-800">Running Forensic Pipeline</h3>
                <p className="text-sm text-gray-400">Three parallel extraction streams via FAISS index</p>
              </div>
              <div className="space-y-3 max-w-sm mx-auto">
                {STEPS.map((s, i) => <ProcessingStep key={s} label={s} done={step > i + 1} active={step === i + 1} />)}
              </div>
            </motion.div>
          )}

          {phase === 'done' && (
            <motion.div key="done" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">

              {/* Verdict */}
              <RiskBadge score={result.riskScore} tier={result.tier} />

              <div className="grid md:grid-cols-5 gap-5">
                {/* Findings */}
                <div className="md:col-span-3 space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-gray-700">Forensic Findings</h3>
                    <span className="text-xs text-gray-400">{result.xaiReasons.length} issues detected</span>
                  </div>
                  {result.xaiReasons.length === 0 ? (
                    <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                      <CheckCircle className="w-10 h-10 text-green-500 mx-auto mb-2" />
                      <p className="font-bold text-green-800">No issues found</p>
                      <p className="text-sm text-green-600 mt-1">All feature vectors are within normal baseline distribution.</p>
                    </div>
                  ) : result.xaiReasons.map((r, i) => (
                    <FindingCard key={i} n={i+1} title={r.field} plain={r.plain} technical={r.technical} severity={r.severity} />
                  ))}

                  {/* Z-score breakdown */}
                  <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                    <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
                      <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider">Feature Z-Score Analysis</h4>
                    </div>
                    <table className="w-full text-sm">
                      <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100">
                        <th className="px-4 py-2 font-medium">Feature</th><th className="px-4 py-2 font-medium">Score</th>
                        <th className="px-4 py-2 font-medium">Baseline Avg</th><th className="px-4 py-2 font-medium">Deviation</th><th className="px-4 py-2 font-medium">Status</th>
                      </tr></thead>
                      <tbody>
                        {[['Metadata', meta, MEANS.metadata.mean, result.zScores.metadata],
                          ['Layout', lay, MEANS.layout.mean, result.zScores.layout],
                          ['Font & Pixel', fnt, MEANS.font.mean, result.zScores.font]
                        ].map(([name, val, avg, z]) => {
                          const bad = Math.abs(z as number) > 2;
                          return (
                            <tr key={name as string} className="border-b border-gray-50 last:border-0 hover:bg-gray-50 transition-colors">
                              <td className="px-4 py-3 font-medium text-gray-700">{name as string}</td>
                              <td className="px-4 py-3 font-mono text-gray-800">{(val as number).toFixed(1)}</td>
                              <td className="px-4 py-3 font-mono text-gray-400">{(avg as number).toFixed(1)}</td>
                              <td className={cx('px-4 py-3 font-mono font-bold', bad ? 'text-red-600' : 'text-gray-400')}>{(z as number).toFixed(2)}σ</td>
                              <td className="px-4 py-3">
                                <span className={cx('text-xs px-2 py-0.5 rounded-full font-semibold', bad ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700')}>
                                  {bad ? 'Flagged' : 'Normal'}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Right panel */}
                <div className="md:col-span-2 space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <MetricPill label="Distance" value={result.dist.toFixed(3)} color="text-blue-600" />
                    <MetricPill label="Threshold" value={THRESHOLD.toFixed(3)} color="text-gray-700" />
                    <MetricPill label="Confidence" value={`${result.confidence.toFixed(0)}%`} color="text-purple-600" />
                    <MetricPill label="Baseline" value={`${N_SAMPLES} docs`} color="text-gray-700" />
                  </div>

                  {/* Chart */}
                  <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                    <div className="px-4 py-3 border-b border-gray-100 bg-gray-50 flex items-center justify-between">
                      <h4 className="text-xs font-bold text-gray-600 uppercase tracking-wider">Feature Cluster Map</h4>
                      <div className="flex gap-3 text-[10px] text-gray-400">
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />Baseline</span>
                        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full inline-block" style={{ background: tc }} />This doc</span>
                      </div>
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                      <ScatterChart margin={{ top: 8, right: 12, bottom: 8, left: -10 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis type="number" dataKey="x" domain={[30, 100]} stroke="#d1d5db" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                        <YAxis type="number" dataKey="y" domain={[40, 100]} stroke="#d1d5db" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                        <Tooltip content={<ChartTip />} />
                        <Scatter data={chartData.filter(d => d.type === 'authentic')} fill="#10b981" opacity={0.4}>
                          {chartData.filter(d => d.type === 'authentic').map((_, i) => <Cell key={i} fill="#10b981" />)}
                        </Scatter>
                        <Scatter data={chartData.filter(d => d.type === 'current')}>
                          {chartData.filter(d => d.type === 'current').map((_, i) => <Cell key={i} fill={tc} r={8} stroke="#fff" strokeWidth={2.5} />)}
                        </Scatter>
                      </ScatterChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>

              {/* Action bar */}
              <div className="bg-white border border-gray-200 rounded-2xl shadow-sm p-5 flex items-center justify-between flex-wrap gap-4">
                <div>
                  <p className="text-sm font-bold text-gray-800">Recommended Action</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {{ green: 'Document has been auto-approved. You may forward it to the processing queue.', yellow: 'Please assign this file to a senior underwriter for manual verification.', red: 'Do not process. Escalate to the Fraud Investigation Unit immediately.' }[result.tier]}
                  </p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => { setPhase('idle'); setStep(0); }}
                    className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-gray-200 text-gray-600 text-sm font-semibold hover:bg-gray-50 transition-colors">
                    <RotateCcw className="w-3.5 h-3.5" /> New Document
                  </button>
                  <button className={cx('flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-bold text-white transition-colors shadow-sm',
                    result.tier === 'red' ? 'bg-red-600 hover:bg-red-700' : result.tier === 'yellow' ? 'bg-amber-500 hover:bg-amber-600' : 'bg-green-600 hover:bg-green-700')}>
                    {{ green: 'Approve & Forward', yellow: 'Send for Review', red: 'Escalate to FIU' }[result.tier]}
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
