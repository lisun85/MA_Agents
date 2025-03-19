export type MessageSender = 'user' | 'assistant' | 'system';

export interface Message {
  id: string;
  text: string;
  timestamp: string;
  sender: MessageSender;
  type?: 'message' | 'typing' | 'error';
  isStreaming?: boolean;
}

export interface WebSocketMessage {
  type: 'message' | 'stream_start' | 'stream_chunk' | 'stream_end' | 'typing' | 'error' | 'greeting' | 'auth_success' | 'system_message';
  message_id?: string;
  content: string;
  sender: MessageSender;
} 