import type { ChatMessage, ChatRole } from '$lib/types/chat';

export const createChatMessage = (role: ChatRole, content: string): ChatMessage => ({
  id: crypto.randomUUID(),
  role,
  content,
  createdAt: new Date()
});

export const createInitialMessages = (): ChatMessage[] => [
  {
    id: 'welcome-1',
    role: 'assistant',
    content:
      "Good evening. I'm here with you. Tell me what kind of scene, mood, or memory you want to explore first.\n\n*For now this is a local UI prototype — the backend will be connected later.*",
    createdAt: new Date()
  }
];

export const createPrototypeAssistantReply = (): ChatMessage =>
  createChatMessage(
    'assistant',
    "I heard you. Backend connection comes later, but the chat flow is ready for a real local model response.\n\n**Next foundation pieces:** character state, memory retrieval, and settings."
  );
