import { useState, useEffect, useRef } from 'react';
import { ChatService, WebSocketEvent } from '../api/chatService';
import { Message } from '../types/message';
import MessageList from './MessageList';
import MessageInput from './MessageInput';

const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
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

    // Subscribe to events
    service.subscribe(WebSocketEvent.CONNECTED, onConnected);
    service.subscribe(WebSocketEvent.DISCONNECTED, onDisconnected);
    service.subscribe(WebSocketEvent.ERROR, onError);
    service.subscribe(WebSocketEvent.MESSAGE_RECEIVED, onMessageReceived);

    // Connect to the WebSocket server
    service.connect();

    // Clean up event listeners on unmount
    return () => {
      service.unsubscribe(WebSocketEvent.CONNECTED, onConnected);
      service.unsubscribe(WebSocketEvent.DISCONNECTED, onDisconnected);
      service.unsubscribe(WebSocketEvent.ERROR, onError);
      service.unsubscribe(WebSocketEvent.MESSAGE_RECEIVED, onMessageReceived);
      service.disconnect();
    };
  }, []);

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
      <header className="bg-blue-600 text-white p-4 shadow-md">
        <h1 className="text-xl font-bold">QuickChat</h1>
        <div className="text-sm">
          {isConnected ? (
            <span className="text-green-200">● Connected</span>
          ) : (
            <span className="text-red-200">● Disconnected</span>
          )}
        </div>
      </header>
      
      <div className="flex-1 overflow-hidden flex flex-col">
        {connectionError && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded m-2">
            {connectionError}
          </div>
        )}
        
        <MessageList messages={messages} />
        
        <div className="p-4 border-t border-gray-200">
          <MessageInput onSendMessage={handleSendMessage} isConnected={isConnected} />
        </div>
      </div>
    </div>
  );
};

export default Chat; 