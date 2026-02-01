'use client';

import { useState } from 'react';
import {
  Video,
  Calendar,
  Clock,
  User,
  Phone,
  Mail,
  CheckCircle,
  X,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { demoBookingApi } from '@/lib/storefront/api';

interface DemoBookingProps {
  productName?: string;
  productId?: string;
  trigger?: React.ReactNode;
  className?: string;
}

// Generate next 7 days for date selection
function getNextDays(days: number = 7) {
  const dates = [];
  const today = new Date();

  for (let i = 1; i <= days; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    dates.push(date);
  }

  return dates;
}

// Available time slots
const timeSlots = [
  { value: '10:00', label: '10:00 AM' },
  { value: '11:00', label: '11:00 AM' },
  { value: '12:00', label: '12:00 PM' },
  { value: '14:00', label: '2:00 PM' },
  { value: '15:00', label: '3:00 PM' },
  { value: '16:00', label: '4:00 PM' },
  { value: '17:00', label: '5:00 PM' },
  { value: '18:00', label: '6:00 PM' },
];

export default function DemoBooking({
  productName,
  productId,
  trigger,
  className,
}: DemoBookingProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<'type' | 'datetime' | 'details' | 'success'>('type');
  const [loading, setLoading] = useState(false);

  const [demoType, setDemoType] = useState<'video' | 'call'>('video');
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [selectedTime, setSelectedTime] = useState('');
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    query: '',
  });

  const availableDates = getNextDays(7);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-IN', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
    });
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.phone) {
      toast.error('Please fill in all required fields');
      return;
    }

    setLoading(true);
    try {
      // Call the demo booking API
      const result = await demoBookingApi.bookDemo({
        product_name: productName || 'General Inquiry',
        customer_name: formData.name,
        phone: formData.phone,
        email: formData.email || undefined,
        address: formData.query || '', // Using query field as notes
        pincode: '',
        preferred_date: selectedDate ? selectedDate.toISOString().split('T')[0] : '',
        preferred_time: timeSlots.find(t => t.value === selectedTime)?.label || selectedTime,
        notes: `Demo Type: ${demoType === 'video' ? 'Video Call' : 'Phone Call'}`,
      });

      setStep('success');
      toast.success(result.message || 'Demo booked successfully!');
    } catch (error) {
      console.error('Failed to book demo:', error);
      toast.error('Failed to book demo. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setStep('type');
    setDemoType('video');
    setSelectedDate(null);
    setSelectedTime('');
    setFormData({ name: '', phone: '', email: '', query: '' });
  };

  const handleClose = () => {
    setOpen(false);
    setTimeout(resetForm, 300); // Reset after animation
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || (
          <Button variant="outline" className={cn('gap-2', className)}>
            <Video className="h-4 w-4" />
            Book Live Demo
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Video className="h-5 w-5 text-primary" />
            {step === 'success' ? 'Demo Booked!' : 'Book a Live Demo'}
          </DialogTitle>
          <DialogDescription>
            {step === 'success'
              ? 'We\'ll contact you shortly to confirm your demo.'
              : 'Get a personalized demo of our water purifiers from our experts.'}
          </DialogDescription>
        </DialogHeader>

        {/* Step 1: Select Demo Type */}
        {step === 'type' && (
          <div className="space-y-4 py-4">
            <Label className="text-sm font-medium">How would you like your demo?</Label>
            <RadioGroup
              value={demoType}
              onValueChange={(value) => setDemoType(value as 'video' | 'call')}
              className="grid grid-cols-2 gap-4"
            >
              <div>
                <RadioGroupItem value="video" id="video" className="peer sr-only" />
                <Label
                  htmlFor="video"
                  className="flex flex-col items-center justify-center p-4 border-2 rounded-lg cursor-pointer peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 hover:bg-muted/50 transition-colors"
                >
                  <Video className="h-8 w-8 mb-2 text-primary" />
                  <span className="font-medium">Video Call</span>
                  <span className="text-xs text-muted-foreground mt-1">See the product live</span>
                </Label>
              </div>
              <div>
                <RadioGroupItem value="call" id="call" className="peer sr-only" />
                <Label
                  htmlFor="call"
                  className="flex flex-col items-center justify-center p-4 border-2 rounded-lg cursor-pointer peer-data-[state=checked]:border-primary peer-data-[state=checked]:bg-primary/5 hover:bg-muted/50 transition-colors"
                >
                  <Phone className="h-8 w-8 mb-2 text-primary" />
                  <span className="font-medium">Phone Call</span>
                  <span className="text-xs text-muted-foreground mt-1">Talk to an expert</span>
                </Label>
              </div>
            </RadioGroup>

            {productName && (
              <div className="bg-muted/50 rounded-lg p-3">
                <p className="text-sm text-muted-foreground">Demo for:</p>
                <p className="font-medium">{productName}</p>
              </div>
            )}

            <Button className="w-full" onClick={() => setStep('datetime')}>
              Continue
            </Button>
          </div>
        )}

        {/* Step 2: Select Date & Time */}
        {step === 'datetime' && (
          <div className="space-y-4 py-4">
            <div>
              <Label className="text-sm font-medium mb-3 block">Select Date</Label>
              <div className="grid grid-cols-4 gap-2">
                {availableDates.map((date) => (
                  <button
                    key={date.toISOString()}
                    onClick={() => setSelectedDate(date)}
                    className={cn(
                      'p-2 rounded-lg border text-center transition-colors',
                      selectedDate?.toDateString() === date.toDateString()
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'hover:bg-muted/50'
                    )}
                  >
                    <div className="text-xs text-muted-foreground">
                      {date.toLocaleDateString('en-IN', { weekday: 'short' })}
                    </div>
                    <div className="font-semibold">
                      {date.getDate()}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {date.toLocaleDateString('en-IN', { month: 'short' })}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <Label className="text-sm font-medium mb-3 block">Select Time</Label>
              <div className="grid grid-cols-4 gap-2">
                {timeSlots.map((slot) => (
                  <button
                    key={slot.value}
                    onClick={() => setSelectedTime(slot.value)}
                    className={cn(
                      'p-2 rounded-lg border text-sm transition-colors',
                      selectedTime === slot.value
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'hover:bg-muted/50'
                    )}
                  >
                    {slot.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('type')} className="flex-1">
                Back
              </Button>
              <Button
                className="flex-1"
                onClick={() => setStep('details')}
                disabled={!selectedDate || !selectedTime}
              >
                Continue
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Contact Details */}
        {step === 'details' && (
          <div className="space-y-4 py-4">
            <div className="bg-muted/50 rounded-lg p-3 flex items-center gap-3">
              <Calendar className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">
                  {selectedDate && formatDate(selectedDate)} at {timeSlots.find(t => t.value === selectedTime)?.label}
                </p>
                <p className="text-sm text-muted-foreground">
                  {demoType === 'video' ? 'Video Call Demo' : 'Phone Call Demo'}
                </p>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <Label htmlFor="name">Full Name *</Label>
                <Input
                  id="name"
                  placeholder="Enter your name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="phone">Phone Number *</Label>
                <Input
                  id="phone"
                  type="tel"
                  placeholder="Enter your phone number"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="email">Email (Optional)</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="Enter your email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="query">Any specific questions? (Optional)</Label>
                <Textarea
                  id="query"
                  placeholder="E.g., What's the difference between RO and UV?"
                  value={formData.query}
                  onChange={(e) => setFormData({ ...formData, query: e.target.value })}
                  rows={3}
                />
              </div>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setStep('datetime')} className="flex-1">
                Back
              </Button>
              <Button
                className="flex-1"
                onClick={handleSubmit}
                disabled={loading || !formData.name || !formData.phone}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Booking...
                  </>
                ) : (
                  'Confirm Booking'
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Step 4: Success */}
        {step === 'success' && (
          <div className="py-8 text-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">Demo Booked Successfully!</h3>
              <p className="text-muted-foreground mt-1">
                We&apos;ll call you on <strong>{formData.phone}</strong> to confirm your appointment.
              </p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4 text-left">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-muted-foreground">Date:</div>
                <div className="font-medium">{selectedDate && formatDate(selectedDate)}</div>
                <div className="text-muted-foreground">Time:</div>
                <div className="font-medium">{timeSlots.find(t => t.value === selectedTime)?.label}</div>
                <div className="text-muted-foreground">Type:</div>
                <div className="font-medium">{demoType === 'video' ? 'Video Call' : 'Phone Call'}</div>
              </div>
            </div>
            <Button onClick={handleClose} className="w-full">
              Done
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
