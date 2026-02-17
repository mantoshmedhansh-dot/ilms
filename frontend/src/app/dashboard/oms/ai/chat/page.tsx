'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Send,
  Bot,
  User,
  Sparkles,
  ArrowRight,
  ShoppingCart,
  Shield,
  Truck,
  RotateCcw,
  ListOrdered,
  MapPin,
  Loader2,
  Lightbulb,
  BarChart3,
} from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api/client';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  data?: Record<string, any> | null;
  suggestions?: string[];
  intent?: string;
  timestamp: Date;
}

const intentIcons: Record<string, any> = {
  order_status: ShoppingCart,
  fraud_check: Shield,
  delivery_promise: Truck,
  routing_status: MapPin,
  return_risk: RotateCcw,
  queue_status: ListOrdered,
  sla_report: BarChart3,
  help: Lightbulb,
};

const starterQueries = [
  'How many orders are pending?',
  'Any suspicious orders?',
  'When will my order arrive?',
  'Show return risk predictions',
  'Show fulfillment queue priorities',
  'What is our SLA performance?',
];

export default function OMSAIChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: async (query: string) => {
      const res = await apiClient.post('/oms-ai/chat', { query });
      return res.data;
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || 'No response generated.',
          data: data.data || null,
          suggestions: data.suggestions || [],
          intent: data.intent,
          timestamp: new Date(),
        },
      ]);
    },
    onError: (error: any) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error?.response?.data?.detail || error.message || 'Unknown error'}. Please try again.`,
          timestamp: new Date(),
        },
      ]);
    },
  });

  const handleSend = (query?: string) => {
    const text = query || input.trim();
    if (!text) return;

    setMessages((prev) => [
      ...prev,
      { role: 'user', content: text, timestamp: new Date() },
    ]);
    setInput('');
    chatMutation.mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatDataValue = (value: any): string => {
    if (typeof value === 'number') {
      if (value >= 10000000) return `${(value / 10000000).toFixed(2)} Cr`;
      if (value >= 100000) return `${(value / 100000).toFixed(2)} L`;
      if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
      return value.toFixed(value % 1 === 0 ? 0 : 2);
    }
    if (Array.isArray(value)) return `${value.length} items`;
    if (typeof value === 'object' && value !== null) return JSON.stringify(value);
    return String(value);
  };

  const renderArrayTable = (key: string, items: any[]) => {
    if (!items.length) return null;
    const cols = Object.keys(items[0]).filter(k => k !== 'id');
    return (
      <div key={key} className="mt-3">
        <p className="text-sm font-medium capitalize mb-2">{key.replace(/_/g, ' ')}</p>
        <div className="overflow-x-auto rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr>
                {cols.map(col => (
                  <th key={col} className="px-3 py-2 text-left font-medium capitalize text-muted-foreground">
                    {col.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.slice(0, 10).map((item, i) => (
                <tr key={i} className="border-t">
                  {cols.map(col => (
                    <td key={col} className="px-3 py-1.5">{formatDataValue(item[col])}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const renderData = (data: Record<string, any>) => {
    if (!data || Object.keys(data).length === 0) return null;

    const arrayEntries = Object.entries(data).filter(
      ([, v]) => Array.isArray(v) && v.length > 0 && typeof v[0] === 'object'
    );
    const flatEntries = Object.entries(data).filter(
      ([, v]) => !Array.isArray(v) && (typeof v !== 'object' || v === null)
    );

    return (
      <div className="mt-3 space-y-3">
        {flatEntries.length > 0 && (
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="grid grid-cols-2 gap-2">
              {flatEntries.map(([key, value]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                  <span className="font-medium">{formatDataValue(value)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        {arrayEntries.map(([key, value]) => renderArrayTable(key, value as any[]))}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <ShoppingCart className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">OMS AI Assistant</h1>
            <p className="text-sm text-muted-foreground">
              Ask questions about orders, fraud, delivery, returns, and more
            </p>
          </div>
          <Badge variant="secondary" className="ml-auto">
            <Sparkles className="h-3 w-3 mr-1" /> AI Powered
          </Badge>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="h-16 w-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-blue-600" />
            </div>
            <h2 className="text-lg font-semibold mb-2">How can I help with order management?</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              I can answer questions about order status, fraud detection, delivery promises,
              routing, return risks, fulfillment priorities, and SLA performance.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg">
              {starterQueries.map((q) => (
                <Button
                  key={q}
                  variant="outline"
                  className="justify-start text-left h-auto py-3 px-4"
                  onClick={() => handleSend(q)}
                >
                  <ArrowRight className="h-4 w-4 mr-2 flex-shrink-0" />
                  <span className="text-sm">{q}</span>
                </Button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => {
          const IntentIcon = msg.intent ? intentIcons[msg.intent] || Bot : Bot;
          return (
            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0 mt-1">
                  <IntentIcon className="h-4 w-4 text-blue-600" />
                </div>
              )}
              <div className={`max-w-[75%] ${
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3'
                  : 'space-y-2'
              }`}>
                {msg.role === 'user' ? (
                  <p className="text-sm">{msg.content}</p>
                ) : (
                  <>
                    <div className="bg-muted/30 border rounded-2xl rounded-tl-sm px-4 py-3">
                      <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    {msg.data && renderData(msg.data)}
                    {msg.suggestions && msg.suggestions.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-2">
                        {msg.suggestions.map((s, sIdx) => (
                          <Button key={sIdx} variant="outline" size="sm" className="h-7 text-xs rounded-full" onClick={() => handleSend(s)}>
                            {s}
                          </Button>
                        ))}
                      </div>
                    )}
                  </>
                )}
                <p className={`text-xs mt-1 ${msg.role === 'user' ? 'text-primary-foreground/60' : 'text-muted-foreground'}`}>
                  {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          );
        })}

        {chatMutation.isPending && (
          <div className="flex gap-3">
            <div className="h-8 w-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
              <Bot className="h-4 w-4 text-blue-600" />
            </div>
            <div className="bg-muted/30 border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Analyzing your query...
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t px-6 py-4">
        <div className="flex gap-3 max-w-3xl mx-auto">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about orders, fraud, delivery, returns..."
            className="flex-1"
            disabled={chatMutation.isPending}
          />
          <Button onClick={() => handleSend()} disabled={!input.trim() || chatMutation.isPending} size="icon">
            {chatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Try: &quot;Show order status&quot; or &quot;Any fraud risks?&quot;
        </p>
      </div>
    </div>
  );
}
