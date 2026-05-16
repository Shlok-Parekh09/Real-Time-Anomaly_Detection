import { HeroSection, HowItWorks, ArchitectureSection, AdvantageSection } from './sections';
import { LiveDemoSection } from './demo';

function Navbar() {
  return (
    <nav className="sticky top-0 z-50 bg-white border-b border-gray-200 shadow-sm px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white font-black text-sm shadow-sm">K</div>
        <div>
          <span className="text-gray-900 font-black text-sm">K-Nearest Forensics</span>
          <span className="hidden md:inline text-gray-400 text-xs ml-2">· Banking Edition</span>
        </div>
      </div>
      <div className="hidden md:flex items-center gap-1">
        {[['How It Works', '#how-it-works'], ['Architecture', '#architecture'], ['Demo', '#demo'], ['Advantage', '#advantage']].map(([l, h]) => (
          <a key={l} href={h} className="px-3 py-1.5 rounded-lg text-sm text-gray-500 hover:text-gray-900 hover:bg-gray-100 transition-all font-medium">{l}</a>
        ))}
      </div>
      <div className="flex items-center gap-2 bg-green-50 border border-green-200 rounded-full px-3 py-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
        <span className="text-xs text-green-700 font-semibold">System Online</span>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-white" style={{ fontFamily: "'Inter', system-ui, sans-serif" }}>
      <Navbar />
      <div id="how-it-works"><HeroSection /></div>
      <HowItWorks />
      <div id="architecture"><ArchitectureSection /></div>
      <LiveDemoSection />
      <div id="advantage"><AdvantageSection /></div>
      <footer className="bg-gray-900 py-10 px-6 text-center">
        <p className="text-white font-black mb-1">K-Nearest Forensics Engine</p>
        <p className="text-gray-500 text-xs mb-4">AI-Powered Document Fraud Detection for Banking Underwriting</p>
        <div className="flex flex-wrap justify-center gap-2 text-[11px] text-gray-600 font-mono">
          {['ANN / FAISS', 'Kafka', 'Redis', 'FastAPI', 'KNN', 'XAI'].map(t => (
            <span key={t} className="px-3 py-1 rounded-full border border-gray-700">{t}</span>
          ))}
        </div>
      </footer>
    </div>
  );
}