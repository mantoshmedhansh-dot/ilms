'use client';

import { useState, useEffect } from 'react';
import {
  MessageSquare,
  ThumbsUp,
  ChevronDown,
  ChevronUp,
  Search,
  Loader2,
  User,
  CheckCircle,
  HelpCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { useAuthStore } from '@/lib/storefront/auth-store';
import { questionsApi, ProductQuestion, ProductAnswer } from '@/lib/storefront/api';
import AskQuestionForm from './ask-question-form';

// Using ProductQuestion and ProductAnswer types from api.ts

interface ProductQAProps {
  productId: string;
  productName: string;
}

export default function ProductQA({ productId, productName }: ProductQAProps) {
  const { isAuthenticated, customer } = useAuthStore();
  const [questions, setQuestions] = useState<ProductQuestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAskForm, setShowAskForm] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<string>>(new Set());
  const [helpfulVotes, setHelpfulVotes] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchQuestions();
  }, [productId]);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const response = await questionsApi.getByProduct(productId);
      setQuestions(response.items);
    } catch (error) {
      console.error('Failed to fetch questions:', error);
      toast.error('Failed to load questions');
    } finally {
      setLoading(false);
    }
  };

  const toggleQuestion = (questionId: string) => {
    setExpandedQuestions((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(questionId)) {
        newSet.delete(questionId);
      } else {
        newSet.add(questionId);
      }
      return newSet;
    });
  };

  const handleVoteHelpful = async (answerId: string) => {
    if (helpfulVotes.has(answerId)) {
      toast.info('You already voted for this answer');
      return;
    }

    if (!isAuthenticated) {
      toast.error('Please login to vote');
      return;
    }

    try {
      await questionsApi.voteHelpful('answer', answerId);
      setHelpfulVotes((prev) => new Set([...prev, answerId]));
      toast.success('Thanks for your feedback!');
    } catch (error) {
      toast.error('Failed to record vote');
    }
  };

  const handleQuestionSubmitted = (newQuestion: ProductQuestion) => {
    setQuestions((prev) => [newQuestion, ...prev]);
    setShowAskForm(false);
    toast.success('Your question has been submitted!');
  };

  const filteredQuestions = questions.filter((q) =>
    q.question_text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="font-semibold text-lg flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Questions & Answers ({questions.length})
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Have a question? Search for answers or ask the community
          </p>
        </div>
        {isAuthenticated && (
          <Button onClick={() => setShowAskForm(!showAskForm)}>
            <HelpCircle className="h-4 w-4 mr-2" />
            Ask a Question
          </Button>
        )}
      </div>

      {/* Ask Question Form */}
      {showAskForm && isAuthenticated && (
        <AskQuestionForm
          productId={productId}
          productName={productName}
          onSubmit={handleQuestionSubmitted}
          onCancel={() => setShowAskForm(false)}
        />
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search questions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Questions List */}
      {filteredQuestions.length === 0 ? (
        <div className="text-center py-12">
          <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
          <h4 className="font-medium mb-2">No questions yet</h4>
          <p className="text-sm text-muted-foreground">
            Be the first to ask a question about this product
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredQuestions.map((question) => (
            <div
              key={question.id}
              className="border rounded-lg overflow-hidden"
            >
              {/* Question */}
              <button
                onClick={() => toggleQuestion(question.id)}
                className="w-full text-left p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-primary">Q:</span>
                      <span className="font-medium">{question.question_text}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        {question.asked_by}
                      </span>
                      <span>{formatDate(question.created_at)}</span>
                      <span>{question.answer_count} answer{question.answer_count !== 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {question.answer_count > 0 && (
                      <Badge variant="secondary" className="text-xs">
                        {question.answer_count} Answer{question.answer_count !== 1 ? 's' : ''}
                      </Badge>
                    )}
                    {expandedQuestions.has(question.id) ? (
                      <ChevronUp className="h-5 w-5 text-muted-foreground" />
                    ) : (
                      <ChevronDown className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                </div>
              </button>

              {/* Answers */}
              {expandedQuestions.has(question.id) && (
                <div className="bg-muted/30 border-t">
                  {question.answers.length === 0 ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                      No answers yet. Check back later!
                    </div>
                  ) : (
                    <div className="divide-y">
                      {question.answers.map((answer) => (
                        <div key={answer.id} className="p-4">
                          <div className="flex items-start gap-3">
                            <span className="font-semibold text-green-600">A:</span>
                            <div className="flex-1">
                              <p className="text-sm">{answer.answer_text}</p>
                              <div className="flex items-center justify-between mt-3">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                  {answer.is_seller_answer ? (
                                    <Badge className="bg-blue-100 text-blue-800 hover:bg-blue-100">
                                      <CheckCircle className="h-3 w-3 mr-1" />
                                      Seller
                                    </Badge>
                                  ) : (
                                    <span>{answer.answered_by}</span>
                                  )}
                                  <span>{formatDate(answer.created_at)}</span>
                                </div>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className={`text-xs ${helpfulVotes.has(answer.id) ? 'text-primary' : ''}`}
                                  onClick={() => handleVoteHelpful(answer.id)}
                                >
                                  <ThumbsUp className={`h-3 w-3 mr-1 ${helpfulVotes.has(answer.id) ? 'fill-current' : ''}`} />
                                  Helpful ({answer.helpful_count + (helpfulVotes.has(answer.id) ? 1 : 0)})
                                </Button>
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Show more */}
      {filteredQuestions.length > 5 && (
        <div className="text-center">
          <Button variant="outline">
            Show More Questions
          </Button>
        </div>
      )}

      {/* Login prompt for non-authenticated users */}
      {!isAuthenticated && (
        <div className="bg-muted/50 rounded-lg p-4 text-center">
          <p className="text-sm text-muted-foreground mb-2">
            Have a question about this product?
          </p>
          <Button variant="outline" asChild>
            <a href={`/account/login?redirect=/products`}>
              Login to Ask a Question
            </a>
          </Button>
        </div>
      )}
    </div>
  );
}
