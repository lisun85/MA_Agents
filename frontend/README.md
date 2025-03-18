# QuickChat Frontend

A React chat application frontend built with TypeScript, Vite, and Tailwind CSS.

## Tech Stack

- Node.js v22.14.0
- React 18
- TypeScript
- Vite.js
- Tailwind CSS
- WebSocket API for real-time communication

## Features

- Real-time chat interface
- WebSocket connection to backend API
- Responsive design with Tailwind CSS
- TypeScript for type safety

## Setup

### Prerequisites

- Node.js v22.14.0
- pnpm package manager

### Installation

1. Install dependencies:

```bash
pnpm install
```

2. Start the development server:

```bash
pnpm dev
```

The application will be available at http://localhost:5173

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── api/             # API services and WebSocket connection
│   ├── components/      # React components
│   ├── types/           # TypeScript type definitions
│   ├── App.tsx          # Main application component
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles and Tailwind imports
├── index.html           # HTML template
├── package.json         # Project dependencies and scripts
├── tsconfig.json        # TypeScript configuration
├── vite.config.ts       # Vite configuration
└── tailwind.config.js   # Tailwind CSS configuration
```

## WebSocket API

The application connects to a WebSocket API at `ws://localhost:5000/chat`. The backend is not included in this repository and will need to be implemented separately.

## Message Format

Messages are exchanged in the following JSON format:

```json
{
  "id": "unique-uuid",
  "text": "Hello, world!",
  "timestamp": "2023-05-15T12:34:56Z",
  "sender": "user" | "bot"
}
```

## Building for Production

```bash
pnpm build
```

This will generate optimized production files in the `dist` directory. 