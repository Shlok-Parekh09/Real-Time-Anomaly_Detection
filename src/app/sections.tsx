import React from 'react';
import { motion } from 'framer-motion';

// ── Hero ─────────────────────────────────────────────────────────────────────
const stats = [
  { label: 'Processing Speed', value: '<50ms', sub: 'ANN via FAISS index' },
  { label: 'Scale', value: '10M+', sub: 'docs in baseline' },
  { label: 'Parallel Streams', value: '3×', sub: 'async microservices' },
  { label: 'Latency Saved', value: '70%', sub: 'vs sequential KNN' },
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-[#F7F7F7] py-24 px-6">
      <div className="absolute inset-0 opacity-[0.02]"
        style={{ backgroundImage: 'linear-gradient(#000 1px,transparent 1px),linear-gradient(90deg,#000 1px,transparent 1px)', backgroundSize: '48px 48px' }} />
      <div className="absolute top-0 left-1/3 w-[500px] h-[500px] bg-violet-400 rounded-full blur-[100px] pointer-events-none opacity-[0.15]" />
      <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-orange-400 rounded-full blur-[100px] pointer-events-none opacity-[0.15]" />

      <div className="relative max-w-5xl mx-auto text-center">
        <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55 }}>
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-neutral-200 bg-white text-neutral-800 text-xs font-semibold mb-7 tracking-wide shadow-[0_2px_10px_rgba(0,0,0,0.03)]">
            <span className="w-2 h-2 rounded-full bg-violet-500 animate-pulse" />
            ANN-Powered · Async Microservices · XAI Narratives · Banking Grade
          </div>
        </motion.div>

        <motion.h1 initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.1 }}
          className="text-5xl md:text-[3.75rem] font-black tracking-tight text-[#131313] mb-5 leading-[1.1]">
          Document Forgery Detection<br />
          <span className="bg-gradient-to-r from-violet-600 via-orange-500 to-violet-600 bg-clip-text text-transparent">
            Built for Real-Time Banking
          </span>
        </motion.h1>

        <motion.p initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.18 }}
          className="text-base text-gray-600 max-w-2xl mx-auto mb-12 leading-relaxed">
          A KNN forensics engine upgraded with Approximate Nearest Neighbors, async microservice pipelines,
          and plain-English XAI outputs — so every underwriter can act in under 5 seconds.
        </motion.p>

        <motion.div initial={{ opacity: 0, y: 22 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.55, delay: 0.26 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto">
          {stats.map(({ label, value, sub }) => (
            <div key={label} className="bg-white border border-[#E5E5E5] rounded-2xl p-5 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:border-violet-300 hover:shadow-[0_4px_20px_-4px_rgba(124,58,237,0.1)] transition-all">
              <div className="text-3xl font-black text-[#131313] mb-1">{value}</div>
              <div className="text-xs font-bold text-neutral-600 mb-0.5">{label}</div>
              <div className="text-[10px] text-neutral-400">{sub}</div>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ── Architecture Section — Full Pipeline Diagram ──────────────────────────────
function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 shrink-0 px-3">
      {label && <div className="text-gray-500 text-[10px] font-bold whitespace-nowrap tracking-wide">{label}</div>}
      <div className="relative flex items-center w-12">
        <div className="w-full h-[2px] bg-blue-100 rounded-full" />
        <svg className="w-4 h-4 text-blue-400 absolute right-0 translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M9 5l7 7-7 7" />
        </svg>
        <motion.div 
          className="w-2 h-2 bg-blue-500 rounded-full absolute left-0 shadow-[0_0_8px_rgba(59,130,246,0.8)]"
          animate={{ x: [0, 40] }}
          transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
        />
      </div>
    </div>
  );
}

function DownArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 my-2">
      {label && <div className="text-[10px] text-gray-500 font-bold text-center max-w-[80px]">{label}</div>}
      <div className="relative flex flex-col items-center h-8">
        <div className="w-[2px] h-full bg-emerald-100 rounded-full" />
        <svg className="w-4 h-4 text-emerald-400 absolute bottom-0 translate-y-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
        </svg>
        <motion.div 
          className="w-2 h-2 bg-emerald-500 rounded-full absolute top-0 shadow-[0_0_8px_rgba(16,185,129,0.8)]"
          animate={{ y: [0, 24] }}
          transition={{ repeat: Infinity, duration: 1.2, ease: "linear" }}
        />
      </div>
    </div>
  );
}

function UpDownArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 my-2">
      <div className="relative flex flex-col items-center h-8 w-6">
        <div className="w-[2px] h-full bg-cyan-200/50 rounded-full" />
        <svg className="w-4 h-4 text-cyan-500 absolute top-0 -translate-y-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 15l7-7 7 7" />
        </svg>
        <svg className="w-4 h-4 text-cyan-500 absolute bottom-0 translate-y-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
      {label && <div className="text-[10px] text-gray-500 font-bold text-center max-w-[80px]">{label}</div>}
    </div>
  );
}

function PipelineBox({ title, sub, items, color, icon }: { title: string; sub?: string; items?: string[]; color: string; icon: string }) {
  const styles = {
    blue: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(59,130,246,0.02)]',
    teal: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(20,184,166,0.02)]',
    green: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(16,185,129,0.02)]',
    violet: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(139,92,246,0.02)]',
    cyan: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(6,182,212,0.02)]',
    amber: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(245,158,11,0.02)]',
    rose: 'border-[#E5E5E5] bg-white text-[#131313] shadow-[inset_0_0_20px_rgba(244,63,94,0.02)]'
  }[color] ?? 'border-[#E5E5E5] bg-white text-[#131313] shadow-sm';

  return (
    <div className={`backdrop-blur-sm border rounded-2xl p-4 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-300 ${styles}`}>
      <div className="flex items-start gap-3 mb-2.5">
        <div className="bg-white/80 p-1.5 rounded-lg shadow-sm border border-white/40">
          <span className="text-xl leading-none">{icon}</span>
        </div>
        <div>
          <div className="text-xs font-black tracking-tight leading-tight">{title}</div>
          {sub && <div className="text-[9px] opacity-70 mt-0.5 font-bold uppercase tracking-wider">{sub}</div>}
        </div>
      </div>
      {items && (
        <ul className="space-y-1.5 pl-0.5 mt-3 border-t border-black/5 pt-2">
          {items.map(it => (
            <li key={it} className="flex items-start gap-1.5 text-[10.5px] opacity-90 font-medium">
              <span className="opacity-40 shrink-0 mt-0.5 text-[8px]">▶</span>
              <span className="leading-snug">{it}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ArchitectureSection() {
  return (
    <section className="bg-[#F7F7F7] py-24 px-6 border-t border-neutral-200 relative">
      <div className="absolute inset-0 opacity-[0.015] pointer-events-none"
        style={{ backgroundImage: 'linear-gradient(#000 1px,transparent 1px),linear-gradient(90deg,#000 1px,transparent 1px)', backgroundSize: '32px 32px' }} />
      
      <div className="max-w-6xl mx-auto relative z-10">
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-[#E5E5E5] text-neutral-600 text-xs font-bold mb-4 shadow-[0_2px_10px_rgba(0,0,0,0.03)] uppercase tracking-widest">
            System Architecture
          </div>
          <h2 className="text-4xl font-black text-[#131313] mb-4 tracking-tight">Real-Time Forensics &amp; Validation Pipeline</h2>
          <p className="text-neutral-500 text-base max-w-2xl mx-auto">
            A high-performance pipeline achieving sub-second latency via FastAPI, OpenCV Error Level Analysis, and local document validation.
          </p>
        </div>

        {/* Main diagram card */}
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }} viewport={{ once: true }}
          className="rounded-[2.5rem] overflow-hidden shadow-[0_20px_60px_-12px_rgba(0,0,0,0.08)] bg-white border border-[#E5E5E5]">

          {/* Runtime header bar */}
          <div className="bg-[#FDFDFD] border-b border-[#E5E5E5] px-8 py-4 flex items-center gap-4">
            <div className="flex items-center gap-2.5 bg-white border border-[#E5E5E5] rounded-xl px-4 py-2 shadow-[0_2px_8px_rgba(0,0,0,0.02)]">
              <span className="text-orange-500 font-black text-sm tracking-wider">⚙️ Local</span>
              <div className="w-px h-4 bg-neutral-200" />
              <span className="text-neutral-600 text-[11px] font-bold uppercase tracking-widest">FastAPI + React Runtime</span>
            </div>
            <span className="text-xs text-neutral-400 font-medium">Docker-ready backend and dashboard</span>
            
            <div className="ml-auto flex items-center gap-3">
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-neutral-200" />
                <span className="w-2.5 h-2.5 rounded-full bg-neutral-200" />
                <span className="w-2.5 h-2.5 rounded-full bg-violet-400 shadow-[0_0_8px_rgba(139,92,246,0.8)] animate-pulse" />
              </div>
              <span className="text-xs text-violet-700 font-bold uppercase tracking-wider bg-violet-50 px-3 py-1 rounded-full border border-violet-100">Live Pipeline</span>
            </div>
          </div>

          <div className="p-8 md:p-12 bg-white relative">
            {/* Background grid inside the diagram */}
            <div className="absolute inset-0 opacity-[0.4] pointer-events-none"
              style={{ backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '16px 16px' }} />

            <div className="flex flex-col items-center gap-8 max-w-4xl mx-auto relative z-10">

              {/* ── Section 1: Document Inputs ────────────────────────── */}
              <div className="flex flex-col items-center gap-4 w-full">
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest text-center bg-white/80 px-4 py-1.5 rounded-full border border-slate-200 shadow-sm">
                  1. Data Sources
                </div>
                <div className="flex flex-wrap justify-center gap-5 w-full">
                  <div className="border border-slate-200/60 bg-white rounded-2xl p-5 w-48 text-center shadow-sm hover:shadow-md hover:-translate-y-1 transition-all">
                    <div className="text-4xl mb-3">🌐</div>
                    <div className="text-xs text-slate-800 font-bold leading-tight">Web Portals & LOS</div>
                  </div>
                  <div className="border border-slate-200/60 bg-white rounded-2xl p-5 w-48 text-center shadow-sm hover:shadow-md hover:-translate-y-1 transition-all">
                    <div className="text-4xl mb-3">📧</div>
                    <div className="text-xs text-slate-800 font-bold">Email Attachments</div>
                  </div>
                </div>
              </div>

              <DownArrow />

              {/* ── Section 2: Ingestion ───────────────────────────────── */}
              <div className="flex flex-col items-center gap-4 w-full">
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest text-center bg-white/80 px-4 py-1.5 rounded-full border border-slate-200 shadow-sm">
                  2. Backend Ingestion
                </div>
                <div className="flex flex-col md:flex-row items-center gap-5">
                  <div className="border border-emerald-200/60 bg-emerald-50/80 backdrop-blur-sm rounded-2xl p-5 w-64 text-center shadow-sm relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-200/30 rounded-bl-full" />
                    <div className="text-4xl mb-3 relative">⚡</div>
                    <div className="text-sm text-emerald-950 font-black relative">FastAPI Gateway</div>
                    <div className="text-[10px] text-emerald-700 mt-1 font-bold relative">High-throughput /api/v1/analyze</div>
                  </div>
                </div>
              </div>

              <DownArrow />

              {/* ── Section 3: Core Forensics Engine ────────────────────── */}
              <div className="w-full border border-blue-200/50 bg-blue-50/30 backdrop-blur-md rounded-[2.5rem] p-6 md:p-8 relative shadow-[inset_0_2px_20px_rgba(59,130,246,0.05)]">
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 px-6 bg-blue-600 text-[10px] font-black text-white uppercase tracking-widest flex items-center gap-2 rounded-full shadow-lg shadow-blue-500/30 py-1.5">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
                  Python Forensics & Local Validation
                </div>
                
                <div className="mt-4">
                  {/* Step 1: Parallel streams */}
                  <div className="mb-6 bg-white/70 backdrop-blur-sm p-5 rounded-2xl border border-blue-100 shadow-sm">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <PipelineBox color="cyan" icon="🔍" title="Metadata Scan"
                        sub="Hidden File Traces"
                        items={['EXIF extraction', 'Software signatures (e.g. Photoshop)']} />
                      <PipelineBox color="violet" icon="🔬" title="OpenCV Engine"
                        sub="Error Level Analysis"
                        items={['Pixel compression variance', 'Color-mapped heatmaps']} />
                      <PipelineBox color="amber" icon="🧮" title="Math Validation"
                        sub="Local Extraction"
                        items={['OCR Text Parsing', 'Financial structure consistency']} />
                    </div>
                  </div>

                  {/* Steps 2-4 */}
                  <div className="flex justify-center mt-6 relative">
                    <div className="flex flex-col items-center">
                      <UpDownArrow />
                      <div className="border border-slate-300 bg-slate-800 text-white rounded-2xl px-8 py-5 text-center shadow-xl relative overflow-hidden group">
                        <div className="absolute inset-0 bg-gradient-to-r from-teal-500/20 to-emerald-500/20 opacity-0 group-hover:opacity-100 transition-opacity" />
                        <div className="text-sm font-black tracking-wide flex items-center gap-2 justify-center relative z-10">
                          <span className="text-teal-400 text-lg">🤖</span> Local Validation Engine
                        </div>
                        <div className="text-[10px] text-slate-300 font-bold mt-1.5 tracking-widest uppercase relative z-10">OCR, PDF parsing, and rule checks</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <DownArrow label="Sub-second processing" />

              {/* ── Section 4: Outputs ─────────────────────────────────── */}
              <div className="flex flex-col items-center gap-4 w-full pt-2">
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest text-center bg-white/80 px-4 py-1.5 rounded-full border border-slate-200 shadow-sm">
                  Final Outputs
                </div>
                <div className="flex flex-wrap justify-center gap-5 w-full">
                  <div className="w-56">
                    <PipelineBox color="amber" icon="📊" title="Risk Score"
                      sub="Direct to LOS"
                      items={['Percentage score (0-100%)', 'Aggregated risk tier']} />
                  </div>
                  <div className="w-56">
                    <PipelineBox color="blue" icon="📑" title="Visual Proof"
                      sub="For Underwriters"
                      items={['ELA Heatmap image', 'Detected anomalies list']} />
                  </div>
                  <div className="w-56 border border-rose-200/60 bg-gradient-to-br from-white to-rose-50/50 rounded-2xl p-5 text-center shadow-sm hover:-translate-y-1 transition-transform cursor-help">
                    <div className="text-4xl mb-3">👤</div>
                    <div className="text-sm font-black text-rose-950">Human Review</div>
                    <div className="text-[10px] text-rose-700 mt-2 font-bold bg-rose-100/60 rounded-full inline-block px-3 py-1">Only when flagged</div>
                  </div>
                </div>
              </div>

            </div>

            {/* Legend */}
            <div className="mt-16 border-t border-slate-200/60 pt-6 flex flex-wrap items-center justify-center gap-x-12 gap-y-4 text-[13px] text-slate-600 bg-white/60 backdrop-blur-md rounded-2xl p-5 shadow-sm relative z-10">
              <span className="flex items-center gap-2.5"><span className="text-indigo-500 bg-indigo-100 p-1.5 rounded-full leading-none">⚡</span> <strong className="text-slate-900 font-black">Local Execution:</strong> No external orchestration</span>
              <span className="flex items-center gap-2.5"><span className="text-blue-500 bg-blue-100 p-1.5 rounded-full leading-none">⏱️</span> <strong className="text-slate-900 font-black">On Upload:</strong> Analysis runs immediately</span>
              <span className="flex items-center gap-2.5"><span className="text-emerald-500 bg-emerald-100 p-1.5 rounded-full leading-none">🔄</span> <strong className="text-slate-900 font-black">Data-Driven:</strong> Uses uploaded file content</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── How It Works ──────────────────────────────────────────────────────────────
const steps = [
  { icon: '📥', n: '01', title: 'Ingest & Parse', desc: 'Document submitted through the app. FastAPI validates the upload and reads the actual file bytes.' },
  { icon: '🔬', n: '02', title: 'Forensic Extraction', desc: 'Metadata, ELA heatmap generation, and copy-move checks run locally with Python and OpenCV.' },
  { icon: '📐', n: '03', title: 'Local Validation', desc: 'PDF parsing or OCR extracts text, then rule-based math checks use the uploaded document values.' },
  { icon: '🧠', n: '04', title: 'Risk Report', desc: 'The backend returns the risk score, anomalies, heatmap, metadata, and validation status to the dashboard.' },
];

export function HowItWorks() {
  return (
    <section className="bg-white py-16 px-6 border-t border-gray-200">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-3xl font-black text-gray-900 text-center mb-2">How It Works</h2>
        <p className="text-gray-500 text-center text-sm mb-12">Four-stage automated forensic pipeline</p>
        <div className="grid md:grid-cols-4 gap-6 relative">
          <div className="hidden md:block absolute top-12 left-[12%] right-[12%] h-px bg-gradient-to-r from-transparent via-blue-200 to-transparent" />
          {steps.map((s, i) => (
            <motion.div key={s.title}
              initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, delay: i * 0.1 }} viewport={{ once: true }}
              className="relative bg-white border border-gray-100 rounded-2xl p-6 text-center hover:border-blue-300 hover:shadow-lg transition-all shadow-sm group cursor-default">
              <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-100 flex items-center justify-center text-2xl mx-auto mb-5 z-10 relative group-hover:scale-110 transition-transform">
                {s.icon}
              </div>
              <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-blue-600 text-white text-xs font-black flex items-center justify-center shadow-md">{s.n}</div>
              <h3 className="text-gray-900 font-bold text-base mb-2">{s.title}</h3>
              <p className="text-gray-500 text-[13px] leading-relaxed">{s.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Business Value Table ──────────────────────────────────────────────────────
const businessValues = [
  { 
    category: 'Risk Protection', 
    problem: 'Fraudsters use sophisticated digital tools to alter PDFs flawlessly. To human eyes, these forged documents look authentic, allowing bad actors to secure fraudulent loans.', 
    impact: 'The software acts as an invisible shield, analyzing pixel variance and hidden metadata to instantly block high-level forgeries before a human sees them, saving millions.' 
  },
  { 
    category: 'Cost Reduction', 
    problem: 'Banks spend massive capital employing large teams to manually review thousands of routine documents—an expensive, fatiguing, and error-prone process.', 
    impact: 'AI handles the heavy lifting instantly. By automatically clearing authentic documents, underwriters are freed to focus their valuable time only on the small percentage of flagged files.' 
  },
  { 
    category: 'Revenue Growth', 
    problem: 'Manual review creates backlogs, forcing honest customers to wait days or weeks for loan approvals. This frustration often drives them to faster competitors.', 
    impact: 'Authentic documents are cleared mathematically in seconds. This allows banks to approve legitimate loans exponentially faster, creating a frictionless customer experience.' 
  },
  { 
    category: 'Infinite Scalability', 
    problem: 'During cyclical rush periods (like tax season or housing booms), high application volumes overwhelm human workers, leading to massive delays and burnout.', 
    impact: 'The machine learning pipeline has infinite elasticity. It processes 10 applications or 10,000 applications at the exact same lightning speed without any fatigue.' 
  },
  { 
    category: 'Compliance & Trust', 
    problem: 'Accidental approvals of fraudulent documents can lead to massive government penalties and severe reputational damage if auditors discover systemic failures.', 
    impact: 'Provides a mathematically proven shield against fraud. With decisions backed by statistical distances and plain-English insights, banks can easily prove their defensive perimeter to regulators.' 
  },
];

export function AdvantageSection() {
  return (
    <section className="bg-gray-50 py-20 px-6 border-t border-gray-200">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 border border-indigo-200 text-indigo-700 text-xs font-semibold mb-4 shadow-sm">
            ADVANTAGE & IMPACT
          </div>
          <h2 className="text-3xl md:text-4xl font-black text-gray-900 mb-4">Business Value &amp; Impact</h2>
          <p className="text-gray-500 text-base max-w-2xl mx-auto leading-relaxed">
            Transitioning from manual reviews to automated forensic analysis transforms operations, 
            slashing costs while fortifying your defensive perimeter.
          </p>
        </div>

        <div className="overflow-hidden rounded-3xl border border-gray-200 shadow-xl bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gradient-to-r from-gray-50 to-gray-100 border-b border-gray-200">
                <th className="px-6 py-5 text-left text-gray-800 font-bold w-[18%] text-[13px] uppercase tracking-wider">Value Category</th>
                <th className="px-6 py-5 text-left text-gray-600 font-semibold w-[41%]">
                  <span className="flex items-center gap-2 text-[13px] uppercase tracking-wider">
                    <span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> The Problem
                  </span>
                </th>
                <th className="px-6 py-5 text-left w-[41%] bg-blue-50/50">
                  <span className="flex items-center gap-2 text-blue-800 font-bold text-[13px] uppercase tracking-wider">
                    <span className="w-2 h-2 rounded-full bg-blue-500 inline-block animate-pulse" /> The K-Nearest Advantage (The Impact)
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {businessValues.map((row, i) => (
                <tr key={row.category} className={`border-b border-gray-100 hover:bg-gray-50/80 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}`}>
                  <td className="px-6 py-5 align-top">
                    <span className="inline-flex items-center justify-center font-bold text-gray-900 text-sm">{row.category}</span>
                  </td>
                  <td className="px-6 py-5 text-gray-600 leading-relaxed align-top">
                    {row.problem}
                  </td>
                  <td className="px-6 py-5 text-blue-900 font-medium leading-relaxed bg-blue-50/20 align-top">
                    {row.impact}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
