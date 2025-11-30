import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { Session, Message, ConnectionStatus, Transcript, AutoAnswer } from '../types';

interface ChatState {
  sessions: Session[];
  currentSessionId: string | null;
  stream: string;
  status: ConnectionStatus;
  liveTranscripts: Transcript[];
  autoAnswer: AutoAnswer | null;

  // Actions
  createSession: () => void;
  deleteSession: (id: string) => void;
  selectSession: (id: string) => void;
  addMessageToCurrent: (message: Message) => void;
  updateCurrentSessionTitle: (title: string) => void;
  setStream: (content: string) => void;
  appendStreamToContent: (content: string) => void;
  commitStreamToMessage: () => void;
  clearStream: () => void;
  setStatus: (status: ConnectionStatus) => void;
  addTranscript: (text: string, source: string) => void;
  clearTranscripts: () => void;
  startAutoAnswer: (question: string) => void;
  appendAutoAnswer: (content: string) => void;
  finishAutoAnswer: () => void;
  dismissAutoAnswer: () => void;
  
  // Computeds
  getCurrentSession: () => Session | undefined;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      stream: '',
      status: 'disconnected',
      liveTranscripts: [],
      autoAnswer: null,

      getCurrentSession: () => {
        const { sessions, currentSessionId } = get();
        return sessions.find((s) => s.id === currentSessionId);
      },

      createSession: () => {
        const { sessions, currentSessionId } = get();
        const currentSession = sessions.find((s) => s.id === currentSessionId);
        
        // Reuse current session if it's empty
        if (currentSession?.messages.length === 0) {
          set({ stream: '' });
          return;
        }
        
        const newSession: Session = {
          id: Date.now().toString(),
          title: 'New Chat',
          date: new Date().toISOString(),
          messages: [],
        };
        set((state) => ({
          sessions: [newSession, ...state.sessions],
          currentSessionId: newSession.id,
          stream: '',
        }));
      },

      deleteSession: (id) => {
        set((state) => {
          const newSessions = state.sessions.filter((s) => s.id !== id);
          let newCurrentId = state.currentSessionId;
          
          if (state.currentSessionId === id) {
            newCurrentId = newSessions.length > 0 ? newSessions[0].id : null;
          }
          
          if (newSessions.length === 0 && state.currentSessionId === id) {
             const replacementSession: Session = {
                id: Date.now().toString(),
                title: 'New Chat',
                date: new Date().toISOString(),
                messages: [],
             };
             return { 
                 sessions: [replacementSession], 
                 currentSessionId: replacementSession.id,
                 stream: ''
             };
          }

          return {
            sessions: newSessions,
            currentSessionId: newCurrentId,
          };
        });
      },

      selectSession: (id) => {
        set({ currentSessionId: id, stream: '' });
      },

      addMessageToCurrent: (message) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === state.currentSessionId
              ? { ...s, messages: [...s.messages, message] }
              : s
          ),
        }));
      },

      updateCurrentSessionTitle: (title) => {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === state.currentSessionId ? { ...s, title } : s
          ),
        }));
      },

      setStream: (content) => set({ stream: content }),
      
      appendStreamToContent: (content) => 
        set((state) => ({ stream: state.stream + content })),

      commitStreamToMessage: () => {
        const { stream, addMessageToCurrent, setStream } = get();
        if (stream) {
          addMessageToCurrent({ role: 'assistant', content: stream });
          setStream('');
        }
      },

      clearStream: () => set({ stream: '' }),
      setStatus: (status) => set({ status }),
      
      addTranscript: (text, source) => {
        set((state) => {
            // Deduplication logic
            const now = Date.now();
            const lastTranscript = state.liveTranscripts[state.liveTranscripts.length - 1];
            
            // If same text and source within 1 second, ignore
            if (lastTranscript && 
                lastTranscript.text === text && 
                lastTranscript.source === source && 
                (now - lastTranscript.timestamp) < 1000) {
                return state;
            }

            return {
                liveTranscripts: [
                    ...state.liveTranscripts,
                    {
                        id: now.toString() + Math.random(),
                        text,
                        source: source as 'user' | 'system',
                        timestamp: now
                    }
                ].slice(-50)
            };
        });
      },
      
      clearTranscripts: () => set({ liveTranscripts: [] }),
      
      startAutoAnswer: (question) => set({
        autoAnswer: {
          id: Date.now().toString(),
          question,
          content: '',
          isStreaming: true,
          timestamp: Date.now()
        }
      }),
      
      appendAutoAnswer: (content) => set((state) => ({
        autoAnswer: state.autoAnswer 
          ? { ...state.autoAnswer, content: state.autoAnswer.content + content }
          : null
      })),
      
      finishAutoAnswer: () => set((state) => ({
        autoAnswer: state.autoAnswer 
          ? { ...state.autoAnswer, isStreaming: false }
          : null
      })),
      
      dismissAutoAnswer: () => set({ autoAnswer: null }),
    }),
    {
      name: 'chat_sessions',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        sessions: state.sessions.filter((s) => s.messages.length > 0),
        currentSessionId: state.currentSessionId 
      }),
    }
  )
);
