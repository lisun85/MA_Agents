import { Message } from '../types/message';

// Events for subscribers
export enum WebSocketEvent {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  MESSAGE_RECEIVED = 'message_received',
  ERROR = 'error',
}

type EventCallback = (data?: any) => void;
type EventSubscribers = Record<WebSocketEvent, EventCallback[]>;

export class ChatService {
  private static instance: ChatService;
  private socket: WebSocket | null = null;
  private subscribers: EventSubscribers = {
    [WebSocketEvent.CONNECTED]: [],
    [WebSocketEvent.DISCONNECTED]: [],
    [WebSocketEvent.MESSAGE_RECEIVED]: [],
    [WebSocketEvent.ERROR]: [],
  };
  
  private constructor() {}
  
  // Singleton pattern
  public static getInstance(): ChatService {
    if (!ChatService.instance) {
      ChatService.instance = new ChatService();
    }
    return ChatService.instance;
  }
  
  public connect(): void {
    // WebSocket URL for backend server
    const wsUrl = 'ws://localhost:8080/chat';
    
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket is already connected');
      return;
    }
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      this.notify(WebSocketEvent.CONNECTED);
    };
    
    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.notify(WebSocketEvent.DISCONNECTED);
    };
    
    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.notify(WebSocketEvent.ERROR, error);
    };
    
    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as Message;
        console.log('Message received:', message);
        this.notify(WebSocketEvent.MESSAGE_RECEIVED, message);
      } catch (error) {
        console.error('Error parsing message:', error);
        this.notify(WebSocketEvent.ERROR, error);
      }
    };
  }
  
  public disconnect(): void {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
  
  public sendMessage(message: string): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }
    
    const messageData: Message = {
      id: crypto.randomUUID(),
      text: message,
      timestamp: new Date().toISOString(),
      sender: 'user',
    };
    
    this.socket.send(JSON.stringify(messageData));
  }
  
  public subscribe(event: WebSocketEvent, callback: EventCallback): void {
    this.subscribers[event].push(callback);
  }
  
  public unsubscribe(event: WebSocketEvent, callback: EventCallback): void {
    this.subscribers[event] = this.subscribers[event].filter(cb => cb !== callback);
  }
  
  private notify(event: WebSocketEvent, data?: any): void {
    this.subscribers[event].forEach(callback => callback(data));
  }
} 