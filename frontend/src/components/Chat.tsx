import { useState, useEffect, useRef } from 'react';
import { ChatService, WebSocketEvent } from '../api/chatService';
import { Message } from '../types/message';
import MessageList from './MessageList';
import MessageInput from './MessageInput';
import InitialForm from './InitialForm';

// Interface for the form data
interface FormData {
  sector: string;
  checkSize: string;
  geographicalLocation: string;
}

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [showInitialForm, setShowInitialForm] = useState(true);
  const [formData, setFormData] = useState<FormData | null>(null);
  const chatService = useRef(ChatService.getInstance());

  useEffect(() => {
    const service = chatService.current;

    // Set up event listeners
    const onConnected = () => {
      setIsConnected(true);
      setConnectionError(null);
    };

    const onDisconnected = () => {
      setIsConnected(false);
    };

    const onError = (error: any) => {
      setConnectionError('Error connecting to chat service. Please try again later.');
      console.error('WebSocket error:', error);
    };

    const onMessageReceived = (message: Message) => {
      setMessages(prevMessages => [...prevMessages, message]);
    };
    
    const onTyping = () => {
      setIsTyping(true);
      setTimeout(() => setIsTyping(false), 1000); // Auto-clear typing indicator after 1s
    };
    
    // Streaming handlers
    const onStreamStart = (message: Message) => {
      setMessages(prevMessages => [...prevMessages, message]);
    };
    
    const onStreamChunk = (data: { id: string, chunk: string }) => {
      setMessages(prevMessages => {
        return prevMessages.map(msg => {
          if (msg.id === data.id) {
            return { ...msg, text: msg.text + data.chunk };
          }
          return msg;
        });
      });
    };
    
    const onStreamEnd = (data: { id: string }) => {
      setMessages(prevMessages => {
        return prevMessages.map(msg => {
          if (msg.id === data.id) {
            return { ...msg, isStreaming: false };
          }
          return msg;
        });
      });
    };

    // Subscribe to events
    service.subscribe(WebSocketEvent.CONNECTED, onConnected);
    service.subscribe(WebSocketEvent.DISCONNECTED, onDisconnected);
    service.subscribe(WebSocketEvent.ERROR, onError);
    service.subscribe(WebSocketEvent.MESSAGE_RECEIVED, onMessageReceived);
    service.subscribe(WebSocketEvent.TYPING, onTyping);
    service.subscribe(WebSocketEvent.STREAM_START, onStreamStart);
    service.subscribe(WebSocketEvent.STREAM_CHUNK, onStreamChunk);
    service.subscribe(WebSocketEvent.STREAM_END, onStreamEnd);

    // Connect to the WebSocket server
    service.connect();

    // Clean up event listeners on unmount
    return () => {
      service.unsubscribe(WebSocketEvent.CONNECTED, onConnected);
      service.unsubscribe(WebSocketEvent.DISCONNECTED, onDisconnected);
      service.unsubscribe(WebSocketEvent.ERROR, onError);
      service.unsubscribe(WebSocketEvent.MESSAGE_RECEIVED, onMessageReceived);
      service.unsubscribe(WebSocketEvent.TYPING, onTyping);
      service.unsubscribe(WebSocketEvent.STREAM_START, onStreamStart);
      service.unsubscribe(WebSocketEvent.STREAM_CHUNK, onStreamChunk);
      service.unsubscribe(WebSocketEvent.STREAM_END, onStreamEnd);
      service.disconnect();
    };
  }, []);

  const handleInitialFormSubmit = (data: FormData) => {
    setFormData(data);
    setShowInitialForm(false);
    // Send form data to the chat service
    chatService.current.setInitialData(data);
  };

  const handleSendMessage = (text: string) => {
    if (!text.trim()) return;
    
    // Create a new message object
    const newMessage: Message = {
      id: crypto.randomUUID(),
      text,
      timestamp: new Date().toISOString(),
      sender: 'user',
    };
    
    // Add the message to our local state
    setMessages(prevMessages => [...prevMessages, newMessage]);
    
    // Send the message through the WebSocket
    chatService.current.sendMessage(text);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      {showInitialForm && <InitialForm onSubmit={handleInitialFormSubmit} />}
      
      <header className="bg-blue-600 text-white p-4 shadow-md">
        <h1 className="text-xl font-bold">QuickChat</h1>
        <div className="text-sm">
          {isConnected ? (
            <span className="text-green-200">● Connected</span>
          ) : (
            <span className="text-red-200">● Disconnected</span>
          )}
        </div>
        {formData && (
          <div className="text-xs mt-1">
            Sector: {formData.sector} | Check Size: {formData.checkSize} | Location: {formData.geographicalLocation}
          </div>
        )}
      </header>
      
      <div className="flex-1 overflow-hidden flex flex-col">
        {connectionError && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded m-2">
            {connectionError}
          </div>
        )}
        
        <MessageList messages={messages} />
        
        {isTyping && (
          <div className="px-4 py-2 text-gray-500 italic">
            Assistant is typing...
          </div>
        )}
        
        <div className="p-4 border-t border-gray-200">
          <MessageInput onSendMessage={handleSendMessage} isConnected={isConnected} />
        </div>
      </div>
    </div>
  );
};

export default Chat; 