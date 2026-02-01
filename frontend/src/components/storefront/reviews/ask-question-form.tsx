'use client';

import { useState } from 'react';
import { Loader2, Send, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { questionsApi, ProductQuestion } from '@/lib/storefront/api';

interface AskQuestionFormProps {
  productId: string;
  productName: string;
  onSubmit: (question: ProductQuestion) => void;
  onCancel: () => void;
}

export default function AskQuestionForm({
  productId,
  productName,
  onSubmit,
  onCancel,
}: AskQuestionFormProps) {
  const { customer } = useAuthStore();
  const [questionText, setQuestionText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!questionText.trim()) {
      setError('Please enter your question');
      return;
    }

    if (questionText.trim().length < 10) {
      setError('Question must be at least 10 characters long');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const newQuestion = await questionsApi.create({
        product_id: productId,
        question_text: questionText.trim(),
      });

      onSubmit(newQuestion);
      setQuestionText('');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to submit question');
    } finally {
      setSubmitting(false);
    }
  };

  const remainingChars = 500 - questionText.length;

  return (
    <form onSubmit={handleSubmit} className="border rounded-lg p-4 bg-muted/30">
      <div className="flex items-center justify-between mb-4">
        <Label className="text-base font-semibold">
          Ask a question about {productName}
        </Label>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={onCancel}
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-4">
        <div>
          <Textarea
            value={questionText}
            onChange={(e) => setQuestionText(e.target.value)}
            placeholder="What would you like to know about this product? Be specific to get helpful answers."
            rows={4}
            maxLength={500}
            className="resize-none"
          />
          <p className={`text-xs mt-1 text-right ${remainingChars < 50 ? 'text-orange-500' : 'text-muted-foreground'}`}>
            {remainingChars} characters remaining
          </p>
        </div>

        <div className="bg-muted/50 rounded-lg p-3 text-sm text-muted-foreground">
          <p className="font-medium mb-1">Tips for a good question:</p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li>Be specific about what you want to know</li>
            <li>Check if your question has already been answered above</li>
            <li>Avoid sharing personal information</li>
          </ul>
        </div>

        <div className="flex gap-3 justify-end">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={submitting || !questionText.trim()}>
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Submit Question
              </>
            )}
          </Button>
        </div>
      </div>
    </form>
  );
}
