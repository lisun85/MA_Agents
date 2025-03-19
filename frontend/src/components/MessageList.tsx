import { useEffect, useRef } from 'react';
import { Message } from '../types/message';

interface MessageListProps {
  messages: Message[];
}

const MessageList = ({ messages }: MessageListProps) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to the bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Format timestamp to a readable time
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-500">
          No messages yet. Start a conversation!
        </div>
      ) : (
        messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`rounded-lg px-4 py-2 max-w-[80%] ${
                message.sender === 'user'
                  ? 'bg-blue-600 text-white'
                  : message.sender === 'system'
                  ? 'bg-yellow-100 text-gray-800 border border-yellow-300'
                  : 'bg-gray-200 text-gray-900'
              } ${message.isStreaming ? 'border-l-4 border-green-500' : ''}`}
            >
              <div className="text-sm mb-1">
                {message.text}
                {message.isStreaming && (
                  <span className="inline-block w-2 h-4 ml-1 bg-green-500 animate-pulse"></span>
                )}
              </div>
              <div className="text-xs text-right opacity-70 flex justify-between items-center">
                <span className="text-xs opacity-60">
                  {message.isStreaming ? 'Streaming...' : message.type === 'typing' ? 'Typing...' : ''}
                </span>
                <span>{formatTime(message.timestamp)}</span>
              </div>
            </div>
          </div>
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList; 