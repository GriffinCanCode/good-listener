import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type {
  AutoAnswer,
  ConnectionStatus,
  Message,
  Session,
  Transcript,
  VADState,
} from '../types';

interface ChatState {
  sessions: Session[];
  currentSessionId: string | null;
  stream: string;
  status: ConnectionStatus;
  micEnabled: boolean;
  liveTranscripts: Transcript[];
  autoAnswer: AutoAnswer | null;
  vad: { user: VADState | null; system: VADState | null };

  // Actions
  createSession: () => void;
  setMicEnabled: (enabled: boolean) => void;
  deleteSession: (id: string) => void;
  selectSession: (id: string) => void;
  addMessageToCurrent: (message: Message) => void;
  updateCurrentSessionTitle: (title: string) => void;
  setStream: (content: string) => void;
  appendStreamToContent: (content: string) => void;
  commitStreamToMessage: () => void;
  clearStream: () => void;
  setStatus: (status: ConnectionStatus) => void;
  addTranscript: (text: string, source: string, speaker: string) => void;
  clearTranscripts: () => void;
  startAutoAnswer: (question: string) => void;
  appendAutoAnswer: (content: string) => void;
  finishAutoAnswer: () => void;
  dismissAutoAnswer: () => void;
  updateVAD: (probability: number, isSpeech: boolean, source: 'user' | 'system') => void;

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
      micEnabled: false,
      liveTranscripts: [],
      autoAnswer: null,
      vad: { user: null, system: null },

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
            newCurrentId = newSessions[0]?.id ?? null;
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
              stream: '',
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
            s.id === state.currentSessionId ? { ...s, messages: [...s.messages, message] } : s
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

      appendStreamToContent: (content) => set((state) => ({ stream: state.stream + content })),

      commitStreamToMessage: () => {
        const { stream, addMessageToCurrent, setStream } = get();
        if (stream) {
          addMessageToCurrent({ role: 'assistant', content: stream });
          setStream('');
        }
      },

      clearStream: () => set({ stream: '' }),
      setStatus: (status) => set({ status }),
      setMicEnabled: (enabled) => set({ micEnabled: enabled }),

      addTranscript: (text, source, speaker) => {
        set((state) => {
          // Deduplication logic
          const now = Date.now();
          const lastTranscript = state.liveTranscripts[state.liveTranscripts.length - 1];

          // If same text and source within 1 second, ignore
          if (
            lastTranscript?.text === text &&
            lastTranscript.source === source &&
            now - lastTranscript.timestamp < 1000
          ) {
            return state;
          }

          return {
            liveTranscripts: [
              ...state.liveTranscripts,
              {
                id: `${now}-${Math.random().toString(36).slice(2)}`,
                text,
                source: source as 'user' | 'system',
                speaker: speaker || (source === 'user' ? 'You' : 'Speaker'),
                timestamp: now,
              },
            ].slice(-50),
          };
        });
      },

      clearTranscripts: () => set({ liveTranscripts: [] }),

      startAutoAnswer: (question) => {
        get().addMessageToCurrent({ role: 'user', content: question });
        set({
          stream: '',
          autoAnswer: {
            id: Date.now().toString(),
            question,
            content: '',
            isStreaming: true,
            timestamp: Date.now(),
          },
        });
      },

      appendAutoAnswer: (content) =>
        set((state) => ({
          stream: state.stream + content,
          autoAnswer: state.autoAnswer
            ? { ...state.autoAnswer, content: state.autoAnswer.content + content }
            : null,
        })),

      finishAutoAnswer: () => {
        get().commitStreamToMessage();
        set((state) => ({
          autoAnswer: state.autoAnswer ? { ...state.autoAnswer, isStreaming: false } : null,
        }));
      },

      dismissAutoAnswer: () => set({ autoAnswer: null }),

      updateVAD: (probability, isSpeech, source) =>
        set((state) => ({
          vad: { ...state.vad, [source]: { probability, isSpeech, source, timestamp: Date.now() } },
        })),
    }),
    {
      name: 'chat_sessions',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sessions: state.sessions.filter((s) => s.messages.length > 0),
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
