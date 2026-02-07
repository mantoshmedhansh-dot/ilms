"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Headphones,
  Plus,
  ArrowLeft,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle,
  MessageSquare,
} from "lucide-react";
import { companyApi } from "@/lib/storefront/api";
import { CompanyInfo } from "@/types/storefront";

const DEMO_CUSTOMER_ID = "00000000-0000-0000-0000-000000000001";

interface ServiceRequest {
  id: string;
  ticket_number: string;
  request_type: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
}

export default function CustomerSupportPage() {
  const router = useRouter();
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [company, setCompany] = useState<CompanyInfo | null>(null);

  // New request form state
  const [newRequest, setNewRequest] = useState({
    request_type: "",
    subject: "",
    description: "",
    priority: "NORMAL",
  });

  useEffect(() => {
    fetchRequests();
    // Fetch company info for support contact
    companyApi.getInfo().then(setCompany).catch(() => null);
  }, []);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/v1/portal/service-requests?customer_id=${DEMO_CUSTOMER_ID}`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          }
        }
      );
      if (response.ok) {
        const data = await response.json();
        setRequests(data.service_requests);
      } else {
        setRequests(getDemoRequests());
      }
    } catch {
      setRequests(getDemoRequests());
    } finally {
      setLoading(false);
    }
  };

  const getDemoRequests = (): ServiceRequest[] => [
    {
      id: "1",
      ticket_number: "SR202401001",
      request_type: "INSTALLATION",
      subject: "Need installation support for water purifier",
      description: "Recently purchased water purifier needs installation at my residence.",
      status: "IN_PROGRESS",
      priority: "HIGH",
      created_at: "2024-01-08T10:30:00",
      updated_at: "2024-01-09T14:00:00",
    },
    {
      id: "2",
      ticket_number: "SR202312045",
      request_type: "WARRANTY",
      subject: "Filter replacement under warranty",
      description: "My water purifier filter needs replacement as per warranty terms.",
      status: "CLOSED",
      priority: "NORMAL",
      created_at: "2023-12-15T09:00:00",
      updated_at: "2023-12-20T16:00:00",
    },
    {
      id: "3",
      ticket_number: "SR202312032",
      request_type: "REPAIR",
      subject: "Water leakage issue",
      description: "There is water leakage from the bottom of the purifier unit.",
      status: "CLOSED",
      priority: "URGENT",
      created_at: "2023-12-10T11:30:00",
      updated_at: "2023-12-12T10:00:00",
    },
  ];

  const handleSubmitRequest = async () => {
    if (!newRequest.request_type || !newRequest.subject || !newRequest.description) {
      alert("Please fill in all required fields");
      return;
    }

    setSubmitting(true);
    try {
      const response = await fetch(
        `/api/v1/portal/service-requests?customer_id=${DEMO_CUSTOMER_ID}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            'Authorization': `Bearer ${localStorage.getItem('access_token') || ''}`,
            'X-Tenant-ID': localStorage.getItem('tenant_id') || '',
          },
          body: JSON.stringify(newRequest),
        }
      );

      if (response.ok) {
        setIsDialogOpen(false);
        setNewRequest({ request_type: "", subject: "", description: "", priority: "NORMAL" });
        fetchRequests();
      } else {
        // Demo mode - add locally
        const newTicket: ServiceRequest = {
          id: String(requests.length + 1),
          ticket_number: `SR${new Date().getFullYear()}${String(new Date().getMonth() + 1).padStart(2, "0")}${String(requests.length + 1).padStart(3, "0")}`,
          ...newRequest,
          status: "OPEN",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        setRequests([newTicket, ...requests]);
        setIsDialogOpen(false);
        setNewRequest({ request_type: "", subject: "", description: "", priority: "NORMAL" });
      }
    } catch {
      // Demo mode fallback
      alert("Request submitted successfully (demo mode)");
      setIsDialogOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "CLOSED":
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case "IN_PROGRESS":
        return <Clock className="h-5 w-5 text-blue-500" />;
      case "OPEN":
        return <AlertCircle className="h-5 w-5 text-orange-500" />;
      default:
        return <MessageSquare className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const config: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      OPEN: { variant: "destructive", label: "Open" },
      IN_PROGRESS: { variant: "secondary", label: "In Progress" },
      PENDING_CUSTOMER: { variant: "outline", label: "Awaiting Response" },
      RESOLVED: { variant: "default", label: "Resolved" },
      CLOSED: { variant: "default", label: "Closed" },
    };
    const c = config[status] || { variant: "outline" as const, label: status };
    return <Badge variant={c.variant}>{c.label}</Badge>;
  };

  const getPriorityBadge = (priority: string) => {
    const config: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; label: string }> = {
      LOW: { variant: "outline", label: "Low" },
      NORMAL: { variant: "secondary", label: "Normal" },
      HIGH: { variant: "destructive", label: "High" },
      URGENT: { variant: "destructive", label: "Urgent" },
    };
    const c = config[priority] || { variant: "outline" as const, label: priority };
    return <Badge variant={c.variant}>{c.label}</Badge>;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const getRequestTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      REPAIR: "Repair",
      INSTALLATION: "Installation",
      WARRANTY: "Warranty",
      GENERAL: "General Query",
      COMPLAINT: "Complaint",
    };
    return labels[type] || type;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={() => router.push("/portal")}>
                <ArrowLeft className="h-5 w-5" />
              </Button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Support Requests</h1>
                <p className="text-sm text-gray-500">Create and track your support tickets</p>
              </div>
            </div>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  New Request
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle>Create Support Request</DialogTitle>
                  <DialogDescription>
                    Fill in the details below to submit a new support request.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <Label htmlFor="request_type">Request Type *</Label>
                    <Select
                      value={newRequest.request_type}
                      onValueChange={(value) =>
                        setNewRequest({ ...newRequest, request_type: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select type" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="INSTALLATION">Installation</SelectItem>
                        <SelectItem value="REPAIR">Repair</SelectItem>
                        <SelectItem value="WARRANTY">Warranty Claim</SelectItem>
                        <SelectItem value="GENERAL">General Query</SelectItem>
                        <SelectItem value="COMPLAINT">Complaint</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="priority">Priority</Label>
                    <Select
                      value={newRequest.priority}
                      onValueChange={(value) =>
                        setNewRequest({ ...newRequest, priority: value })
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select priority" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="LOW">Low</SelectItem>
                        <SelectItem value="NORMAL">Normal</SelectItem>
                        <SelectItem value="HIGH">High</SelectItem>
                        <SelectItem value="URGENT">Urgent</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="subject">Subject *</Label>
                    <Input
                      id="subject"
                      placeholder="Brief description of the issue"
                      value={newRequest.subject}
                      onChange={(e) =>
                        setNewRequest({ ...newRequest, subject: e.target.value })
                      }
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="description">Description *</Label>
                    <Textarea
                      id="description"
                      placeholder="Provide detailed information about your request..."
                      rows={4}
                      value={newRequest.description}
                      onChange={(e) =>
                        setNewRequest({ ...newRequest, description: e.target.value })
                      }
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleSubmitRequest} disabled={submitting}>
                    {submitting ? "Submitting..." : "Submit Request"}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Your Support Tickets</CardTitle>
            <CardDescription>
              View the status of your support requests and add comments
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                <p className="mt-2 text-gray-500">Loading requests...</p>
              </div>
            ) : requests.length === 0 ? (
              <div className="text-center py-8">
                <Headphones className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">No support requests yet</p>
                <Button onClick={() => setIsDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Your First Request
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {requests.map((request) => (
                  <div
                    key={request.id}
                    className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => router.push(`/portal/support/${request.id}`)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        {getStatusIcon(request.status)}
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium text-gray-900">
                              {request.ticket_number}
                            </span>
                            <Badge variant="outline">
                              {getRequestTypeLabel(request.request_type)}
                            </Badge>
                          </div>
                          <p className="text-sm font-medium text-gray-800">
                            {request.subject}
                          </p>
                          <p className="text-sm text-gray-500 mt-1 line-clamp-1">
                            {request.description}
                          </p>
                          <p className="text-xs text-gray-400 mt-2">
                            Created: {formatDate(request.created_at)} | Updated:{" "}
                            {formatDate(request.updated_at)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex flex-col items-end gap-1">
                          {getStatusBadge(request.status)}
                          {getPriorityBadge(request.priority)}
                        </div>
                        <ChevronRight className="h-5 w-5 text-gray-400" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Quick Help Section */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 text-center">
              <div className="h-12 w-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Headphones className="h-6 w-6 text-blue-600" />
              </div>
              <h3 className="font-medium mb-2">Call Support</h3>
              <p className="text-sm text-gray-500">{company?.phone || '1800-123-4567'}</p>
              <p className="text-xs text-gray-400">Mon-Sat, 9 AM - 6 PM</p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 text-center">
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <MessageSquare className="h-6 w-6 text-green-600" />
              </div>
              <h3 className="font-medium mb-2">WhatsApp</h3>
              <p className="text-sm text-gray-500">{company?.phone ? `+91 ${company.phone}` : '+91 98765 43210'}</p>
              <p className="text-xs text-gray-400">24/7 Available</p>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6 text-center">
              <div className="h-12 w-12 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="h-6 w-6 text-purple-600" />
              </div>
              <h3 className="font-medium mb-2">FAQs</h3>
              <p className="text-sm text-gray-500">Common Questions</p>
              <p className="text-xs text-gray-400">Find quick answers</p>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
