'use client';

import { useState, useRef, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  Send,
  Bot,
  User,
  Sparkles,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  Package,
  BarChart3,
  Loader2,
  MessageSquare,
  Lightbulb,
} from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { apiClient } from '@/lib/api/client';

interface ChatAction {
  label: string;
  endpoint: string;
  method: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  data?: Record<string, any> | null;
  suggestions?: string[];
  actions?: ChatAction[];
  intent?: string;
  timestamp: Date;
}

const intentIcons: Record<string, any> = {
  FORECAST_STATUS: TrendingUp,
  FORECAST_ACCURACY: BarChart3,
  DEMAND_SUMMARY: BarChart3,
  SUPPLY_STATUS: Package,
  STOCKOUT_RISK: AlertTriangle,
  OVERSTOCK_CHECK: Package,
  SCENARIO_COMPARE: BarChart3,
  SIGNAL_STATUS: Sparkles,
  INVENTORY_HEALTH: Package,
  GAP_ANALYSIS: TrendingUp,
  AGENT_ALERTS: AlertTriangle,
  HELP: Lightbulb,
};

const starterQueries = [
  'What is the demand forecast for next quarter?',
  'Show me stockout risks',
  'How accurate are our forecasts?',
  'Any alerts from AI agents?',
  'Compare our scenarios',
  'What is the inventory health?',
];

export default function SNOPChatPage() {
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
      const res = await apiClient.post('/snop/chat', { query });
      return res.data;
    },
    onSuccess: (data, query) => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response || data.narrative || 'No response generated.',
          data: data.data || null,
          suggestions: data.suggestions || [],
          actions: data.actions || [],
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
    return String(value);
  };

  const renderData = (data: Record<string, any>) => {
    if (!data || Object.keys(data).length === 0) return null;

    // If data has nested objects, render as cards
    const hasNested = Object.values(data).some(
      (v) => typeof v === 'object' && v !== null && !Array.isArray(v)
    );

    if (hasNested) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
          {Object.entries(data).map(([key, value]) => {
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
              return (
                <Card key={key} className="bg-muted/50">
                  <CardHeader className="pb-2 pt-3 px-4">
                    <CardTitle className="text-sm font-medium capitalize">
                      {key.replace(/_/g, ' ')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="px-4 pb-3">
                    <div className="space-y-1">
                      {Object.entries(value as Record<string, any>).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-sm">
                          <span className="text-muted-foreground capitalize">
                            {k.replace(/_/g, ' ')}
                          </span>
                          <span className="font-medium">{formatDataValue(v)}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            }
            return null;
          })}
        </div>
      );
    }

    // Flat data — render as a simple list
    return (
      <div className="bg-muted/50 rounded-lg p-3 mt-3">
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(data).map(([key, value]) => (
            <div key={key} className="flex justify-between text-sm">
              <span className="text-muted-foreground capitalize">
                {key.replace(/_/g, ' ')}
              </span>
              <span className="font-medium">{formatDataValue(value)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
            <MessageSquare className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">S&OP AI Assistant</h1>
            <p className="text-sm text-muted-foreground">
              Ask questions about demand, supply, forecasts, inventory, and more
            </p>
          </div>
          <Badge variant="secondary" className="ml-auto">
            <Sparkles className="h-3 w-3 mr-1" />
            AI Powered
          </Badge>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-lg font-semibold mb-2">How can I help with S&OP planning?</h2>
            <p className="text-muted-foreground mb-6 max-w-md">
              I can answer questions about demand forecasts, supply plans, inventory health,
              stockout risks, scenario analysis, and more.
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
            <div
              key={idx}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-1">
                  <IntentIcon className="h-4 w-4 text-primary" />
                </div>
              )}

              <div
                className={`max-w-[75%] ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3'
                    : 'space-y-2'
                }`}
              >
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
                          <Button
                            key={sIdx}
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs rounded-full"
                            onClick={() => handleSend(s)}
                          >
                            {s}
                          </Button>
                        ))}
                      </div>
                    )}
                  </>
                )}

                <p
                  className={`text-xs mt-1 ${
                    msg.role === 'user' ? 'text-primary-foreground/60' : 'text-muted-foreground'
                  }`}
                >
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
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
              <Bot className="h-4 w-4 text-primary" />
            </div>
            <div className="bg-muted/30 border rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Analyzing your query...
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
            placeholder="Ask about demand forecasts, supply plans, inventory health..."
            className="flex-1"
            disabled={chatMutation.isPending}
          />
          <Button
            onClick={() => handleSend()}
            disabled={!input.trim() || chatMutation.isPending}
            size="icon"
          >
            {chatMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Try: &quot;Show me stockout risks&quot; or &quot;How accurate are our forecasts?&quot;
        </p>
      </div>
    </div>
  );
}
