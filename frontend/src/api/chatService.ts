import { Message, WebSocketMessage } from '../types/message';

// Events for subscribers
export enum WebSocketEvent {
  CONNECTED = 'connected',
  DISCONNECTED = 'disconnected',
  MESSAGE_RECEIVED = 'message_received',
  STREAM_START = 'stream_start',
  STREAM_CHUNK = 'stream_chunk',
  STREAM_END = 'stream_end',
  TYPING = 'typing',
  ERROR = 'error',
}

// Type for form data
export interface InitialFormData {
  sector: string;
  checkSize: string;
  geographicalLocation: string;
}

export class ChatService {
  private static instance: ChatService;
  private socket: WebSocket | null = null;
  private subscribers: Map<string, Function[]> = new Map();
  private initialData: InitialFormData | null = null;

  private constructor() {}

  public static getInstance(): ChatService {
    if (!ChatService.instance) {
      ChatService.instance = new ChatService();
    }
    return ChatService.instance;
  }
  
  public subscribe(event: WebSocketEvent, callback: Function): void {
    if (!this.subscribers.has(event)) {
      this.subscribers.set(event, []);
    }
    this.subscribers.get(event)?.push(callback);
  }
  
  public unsubscribe(event: WebSocketEvent, callback: Function): void {
    const callbacks = this.subscribers.get(event);
    if (callbacks) {
      const index = callbacks.indexOf(callback);
      if (index !== -1) {
        callbacks.splice(index, 1);
      }
    }
  }
  
  private notify(event: WebSocketEvent, data?: any): void {
    const callbacks = this.subscribers.get(event);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }
  
  public connect(): void {
    // WebSocket URL using the current window location - dynamically gets the host and port
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/chat`;
    
    if (this.socket?.readyState === WebSocket.OPEN) {
      console.log('WebSocket is already connected');
      return;
    }
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket connected');
      // Send authentication token immediately after connection
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({
          type: "auth",
          token: "test"
        }));
      }
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
        const wsMessage = JSON.parse(event.data) as WebSocketMessage;
        console.log('Message received:', wsMessage);
        
        // Convert websocket message to appropriate event
        switch (wsMessage.type) {
          case 'stream_start':
            this.handleStreamStart(wsMessage);
            break;
          case 'stream_chunk':
            this.handleStreamChunk(wsMessage);
            break;
          case 'stream_end':
            this.handleStreamEnd(wsMessage);
            break;
          case 'typing':
            this.notify(WebSocketEvent.TYPING);
            break;
          case 'error':
            this.notify(WebSocketEvent.ERROR, wsMessage.content);
            break;
          case 'system_message':
            console.log('System message:', wsMessage.content);
            // Don't display system messages to the user
            break;
          case 'message':
          case 'greeting':
            this.handleMessage(wsMessage);
            break;
          default:
            console.log('Unhandled message type:', wsMessage.type);
        }
      } catch (error) {
        console.error('Error parsing message:', error);
        this.notify(WebSocketEvent.ERROR, error);
      }
    };
  }
  
  private handleStreamStart(wsMessage: WebSocketMessage): void {
    const message: Message = {
      id: wsMessage.message_id || crypto.randomUUID(),
      text: wsMessage.content,
      timestamp: new Date().toISOString(),
      sender: wsMessage.sender,
      isStreaming: true,
    };
    
    this.notify(WebSocketEvent.STREAM_START, message);
  }
  
  private handleStreamChunk(wsMessage: WebSocketMessage): void {
    const id = wsMessage.message_id || '';
    const chunk = wsMessage.content || '';
    
    this.notify(WebSocketEvent.STREAM_CHUNK, { id, chunk });
  }
  
  private handleStreamEnd(wsMessage: WebSocketMessage): void {
    const id = wsMessage.message_id || '';
    
    this.notify(WebSocketEvent.STREAM_END, { id });
  }
  
  private handleMessage(wsMessage: WebSocketMessage): void {
    const message: Message = {
      id: wsMessage.message_id || crypto.randomUUID(),
      text: wsMessage.content,
      timestamp: new Date().toISOString(),
      sender: wsMessage.sender,
      type: wsMessage.type as any,
    };
    
    this.notify(WebSocketEvent.MESSAGE_RECEIVED, message);
  }
  
  public disconnect(): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.close();
    }
  }
  
  public setInitialData(data: InitialFormData): void {
    this.initialData = data;
    
    // Send initialization data to the server
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      // First send init_data to set params on server side
      this.socket.send(JSON.stringify({
        type: "init_data",
        sector: data.sector,
        check_size: data.checkSize,
        geographical_location: data.geographicalLocation
      }));

      // Then immediately send a system message to trigger the reasoning process
      setTimeout(() => {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
          const messageObject = {
            content: "init_reasoning",
            sector: data.sector,
            check_size: data.checkSize,
            geographical_location: data.geographicalLocation
          };
          
          this.socket.send(JSON.stringify({
            type: "message",
            content: JSON.stringify(messageObject)
          }));
        }
      }, 500); // Small delay to ensure init_data is processed first
    }
  }
  
  public sendMessage(message: string): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.error('WebSocket is not connected');
      return;
    }
    
    // Create a message object with the content and form data
    const messageObject = {
      content: message,
      sector: this.initialData?.sector || '',
      check_size: this.initialData?.checkSize || '',
      geographical_location: this.initialData?.geographicalLocation || ''
    };

    // Send the message as a JSON string
    this.socket.send(JSON.stringify({
      type: "message",
      content: JSON.stringify(messageObject)
    }));
  }
} 