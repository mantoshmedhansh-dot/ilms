'use client';

import { useState } from 'react';
import { MessageCircle, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WhatsAppButtonProps {
  phoneNumber?: string;
  message?: string;
  className?: string;
}

export default function WhatsAppButton({
  phoneNumber = '919311939076', // Default Aquapurite number (without +)
  message = 'Hi! I have a question about Aquapurite water purifiers.',
  className,
}: WhatsAppButtonProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isVisible, setIsVisible] = useState(true);

  const whatsappUrl = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(message)}`;

  if (!isVisible) return null;

  return (
    <div className={cn('fixed bottom-24 right-4 z-50 flex flex-col items-end gap-2', className)}>
      {/* Expanded Chat Prompt */}
      {isExpanded && (
        <div className="bg-white rounded-lg shadow-xl border border-gray-200 w-72 overflow-hidden animate-in slide-in-from-bottom-2 duration-200">
          {/* Header */}
          <div className="bg-[#25D366] px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center">
                <MessageCircle className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold text-sm">Aquapurite Support</p>
                <p className="text-white/80 text-xs">Typically replies instantly</p>
              </div>
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-white/80 hover:text-white transition-colors"
              aria-label="Close chat prompt"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="p-4 bg-[#ECE5DD]">
            <div className="bg-white rounded-lg p-3 shadow-sm max-w-[85%]">
              <p className="text-sm text-gray-800">
                Hello! How can we help you today?
              </p>
              <p className="text-xs text-gray-500 mt-1">Just now</p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="p-3 space-y-2 bg-white border-t">
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full bg-[#25D366] hover:bg-[#20BD5A] text-white text-center py-2.5 rounded-lg font-medium text-sm transition-colors"
            >
              Start Chat
            </a>
            <div className="grid grid-cols-2 gap-2">
              <a
                href={`https://wa.me/${phoneNumber}?text=${encodeURIComponent('I want to know about water purifier prices')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-center py-2 px-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
              >
                Product Prices
              </a>
              <a
                href={`https://wa.me/${phoneNumber}?text=${encodeURIComponent('I need help with installation')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-center py-2 px-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
              >
                Installation Help
              </a>
              <a
                href={`https://wa.me/${phoneNumber}?text=${encodeURIComponent('I want to book a service')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-center py-2 px-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
              >
                Book Service
              </a>
              <a
                href={`https://wa.me/${phoneNumber}?text=${encodeURIComponent('I have a query about my order')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-center py-2 px-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700"
              >
                Order Query
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={cn(
          'group flex items-center gap-2 bg-[#25D366] hover:bg-[#20BD5A] text-white rounded-full shadow-lg transition-all duration-300',
          isExpanded ? 'p-3' : 'pl-4 pr-5 py-3'
        )}
        aria-label={isExpanded ? 'Close WhatsApp chat' : 'Open WhatsApp chat'}
      >
        <MessageCircle className="h-6 w-6" />
        {!isExpanded && (
          <span className="font-medium text-sm whitespace-nowrap">Chat with us</span>
        )}
      </button>

      {/* Pulse animation when collapsed */}
      {!isExpanded && (
        <span className="absolute bottom-0 right-0 w-full h-full rounded-full bg-[#25D366] animate-ping opacity-20 pointer-events-none" />
      )}
    </div>
  );
}
