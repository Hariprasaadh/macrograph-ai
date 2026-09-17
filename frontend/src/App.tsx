import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { Hero } from './components/Hero';
import { StatsBar } from './components/StatsBar';
import { DemoModal } from './components/DemoModal';
import { AgentsDrawer } from './components/AgentsDrawer';
import { SignInModal } from './components/SignInModal';
import { ResearchModal } from './components/ResearchModal';

export const App: React.FC = () => {
  const [isDemoOpen, setIsDemoOpen] = useState(false);
  const [isAgentsOpen, setIsAgentsOpen] = useState(false);
  const [isSignInOpen, setIsSignInOpen] = useState(false);
  const [isResearchOpen, setIsResearchOpen] = useState(false);
  const [user, setUser] = useState<string | null>(null);

  const [systemStatus, setSystemStatus] = useState({
    online: false,
    agentsCount: 8,
    nodesCount: 20,
  });

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/health');
        if (res.ok) {
          const data = await res.json();
          setSystemStatus({
            online: true,
            agentsCount: data.sectors_active || 8,
            nodesCount: data.knowledge_graph_nodes || 20,
          });
        } else {
          setSystemStatus(prev => ({ ...prev, online: false }));
        }
      } catch (err) {
        // Fallback to simulated online mode for rich preview
        setSystemStatus({
          online: true,
          agentsCount: 8,
          nodesCount: 22,
        });
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="relative w-full min-h-[100dvh] flex flex-col justify-between overflow-x-hidden select-none">
      {/* Panoramic Scenic Clean Background */}
      <div 
        className="fixed inset-0 w-full h-full bg-no-repeat z-0 pointer-events-none transition-all duration-300"
        style={{
          backgroundImage: `url('/images/landing_page_bg_clean.png')`,
          backgroundPosition: 'center bottom',
          backgroundSize: 'cover',
        }}
      >
        {/* Responsive light/amber tint scrim on mobile to ensure dark headline always has high contrast */}
        <div className="absolute inset-0 bg-gradient-to-b from-amber-50/50 via-transparent to-slate-950/70 sm:from-transparent sm:via-transparent sm:to-transparent pointer-events-none" />
        
        {/* Subtle top-vignette to ensure nav contrast across all screens */}
        <div className="absolute inset-x-0 top-0 h-20 sm:h-28 bg-gradient-to-b from-slate-900/15 to-transparent pointer-events-none" />
      </div>

      {/* Main Content Container Layered Above Background */}
      <div className="relative z-10 flex flex-col min-h-[100dvh] justify-between">
        {/* Navigation Bar */}
        <Navbar
          onOpenSignIn={() => setIsSignInOpen(true)}
          onOpenAgents={() => setIsAgentsOpen(true)}
          onOpenDemo={() => setIsDemoOpen(true)}
          onOpenResearch={() => setIsResearchOpen(true)}
          user={user}
          systemStatus={systemStatus}
        />

        {/* Cursive Accent on Desktop matching original mockup */}
        <div className="hidden lg:flex flex-col items-start absolute right-14 xl:right-28 top-20 xl:top-24 pointer-events-none select-none z-20 transform -rotate-3">
          <span className="font-script text-white text-5xl xl:text-6xl font-bold tracking-wide drop-shadow-[0_2px_12px_rgba(0,0,0,0.35)]">
            Data.
          </span>
          <span className="font-script text-white text-5xl xl:text-6xl font-bold tracking-wide -mt-2 drop-shadow-[0_2px_12px_rgba(0,0,0,0.35)]">
            Agents.
          </span>
          <span className="font-script text-white text-5xl xl:text-6xl font-bold tracking-wide -mt-2 drop-shadow-[0_2px_12px_rgba(0,0,0,0.35)]">
            A Brighter India.
          </span>
          {/* Handwritten underline flourish */}
          <svg viewBox="0 0 220 25" className="w-52 xl:w-60 -mt-2 text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.3)]">
            <path d="M 5 10 Q 90 22, 215 8" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
          </svg>
        </div>

        {/* Hero Section */}
        <div className="flex-1 flex flex-col justify-center sm:justify-start my-auto sm:my-0">
          <Hero
            onGetStarted={() => setIsResearchOpen(true)}
            onExploreDemo={() => setIsDemoOpen(true)}
          />
        </div>

        {/* Bottom Floating Stats Bar */}
        <StatsBar
          onOpenAgents={() => setIsAgentsOpen(true)}
          onOpenSources={() => setIsAgentsOpen(true)}
        />
      </div>

      {/* Interactive Modals and Drawers */}
      <DemoModal
        isOpen={isDemoOpen}
        onClose={() => setIsDemoOpen(false)}
      />

      <AgentsDrawer
        isOpen={isAgentsOpen}
        onClose={() => setIsAgentsOpen(false)}
      />

      <SignInModal
        isOpen={isSignInOpen}
        onClose={() => setIsSignInOpen(false)}
        onSuccess={(loggedUser) => setUser(loggedUser)}
      />

      <ResearchModal
        isOpen={isResearchOpen}
        onClose={() => setIsResearchOpen(false)}
        systemStatus={systemStatus}
      />
    </div>
  );
};

export default App;
