import { useEffect } from 'react';
import UnderwriterDashboard from './components/UnderwriterDashboard';

function App() {
  useEffect(() => {
    // Initialize Puter.js when app loads
    if (typeof window !== 'undefined' && window.puter) {
      console.log('[APP] Puter.js loaded successfully');
      // Puter will handle authentication automatically when AI is first used
    } else {
      console.warn('[APP] Puter.js not loaded. Please check internet connection.');
    }
  }, []);

  return (
    <UnderwriterDashboard />
  )
}

export default App;
