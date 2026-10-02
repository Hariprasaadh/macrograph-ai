import React, { useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { UserProfile } from './types';
import { LandingPage } from './components/LandingPage';
import { GoogleAuthModal } from './components/GoogleAuthModal';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './components/DashboardView';
import { ChatWorkspace } from './components/ChatWorkspace';
import { KnowledgeGraphView } from './components/KnowledgeGraphView';
import { A2ARegistryView } from './components/A2ARegistryView';

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const saved = localStorage.getItem('macrograph_user');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [googleClientId, setGoogleClientId] = useState<string>(() => {
    return (
      (import.meta as any).env?.VITE_GOOGLE_CLIENT_ID ||
      localStorage.getItem('macrograph_google_client_id') ||
      ''
    );
  });

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [currentView, setCurrentView] = useState<'landing' | 'dashboard' | 'chat' | 'knowledge_graph' | 'a2a_registry'>(() => {
    const saved = localStorage.getItem('macrograph_user');
    return saved ? 'dashboard' : 'landing';
  });

  const [selectedAgentId, setSelectedAgentId] = useState<string>('orchestrator');

  const handleLoginSuccess = (profile: UserProfile) => {
    setUser(profile);
    localStorage.setItem('macrograph_user', JSON.stringify(profile));
    setIsAuthModalOpen(false);
    setCurrentView('dashboard');
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('macrograph_user');
    setCurrentView('landing');
  };

  const handleSaveClientId = (id: string) => {
    setGoogleClientId(id);
    localStorage.setItem('macrograph_google_client_id', id);
  };

  // Safe fallback to prevent GoogleOAuthProvider throwing when clientId is blank
  const activeClientId = googleClientId || '764518928371-dummyid.apps.googleusercontent.com';

  return (
    <GoogleOAuthProvider clientId={activeClientId}>
      {/* If on landing view or unauthenticated */}
      {currentView === 'landing' || !user ? (
        <>
          <LandingPage
            isAuthenticated={!!user}
            onOpenAuth={() => setIsAuthModalOpen(true)}
            onEnterWorkspace={() => setCurrentView('dashboard')}
          />
          <GoogleAuthModal
            isOpen={isAuthModalOpen}
            onClose={() => setIsAuthModalOpen(false)}
            onSuccess={handleLoginSuccess}
            clientId={googleClientId}
            onSaveClientId={handleSaveClientId}
          />
        </>
      ) : (
        <div className="flex h-screen w-screen overflow-hidden bg-background text-slate-100 font-sans">
          {/* Left Sidebar */}
          <Sidebar
            currentView={currentView as 'dashboard' | 'chat' | 'knowledge_graph' | 'a2a_registry'}
            onSelectView={(view) => setCurrentView(view)}
            selectedAgentId={selectedAgentId}
            onSelectAgent={(agentId) => setSelectedAgentId(agentId)}
            user={user}
            onLogout={handleLogout}
          />

          {/* Main View Area */}
          <main className="flex-1 flex flex-col h-screen overflow-hidden">
            {currentView === 'dashboard' && <DashboardView />}
            {currentView === 'chat' && (
              <ChatWorkspace
                selectedAgentId={selectedAgentId}
                onSelectAgent={(agentId) => setSelectedAgentId(agentId)}
              />
            )}
            {currentView === 'knowledge_graph' && <KnowledgeGraphView />}
            {currentView === 'a2a_registry' && <A2ARegistryView />}
          </main>
        </div>
      )}
    </GoogleOAuthProvider>
  );
};

export default App;
