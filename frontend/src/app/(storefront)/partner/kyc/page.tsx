'use client';

import { useEffect, useState, useRef } from 'react';
import { usePartnerStore } from '@/lib/storefront/partner-store';
import { partnerKYCApi, BankDetails } from '@/lib/storefront/partner-api';
import { uploadsApi } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  FileCheck,
  Upload,
  CheckCircle,
  Clock,
  AlertCircle,
  Loader2,
  CreditCard,
  User,
  Building2,
  FileImage,
  X,
} from 'lucide-react';

const statusColors: Record<string, { bg: string; icon: React.ReactNode }> = {
  VERIFIED: { bg: 'bg-green-100 text-green-800', icon: <CheckCircle className="h-4 w-4" /> },
  PENDING: { bg: 'bg-yellow-100 text-yellow-800', icon: <Clock className="h-4 w-4" /> },
  SUBMITTED: { bg: 'bg-blue-100 text-blue-800', icon: <Clock className="h-4 w-4" /> },
  REJECTED: { bg: 'bg-red-100 text-red-800', icon: <AlertCircle className="h-4 w-4" /> },
};

interface KYCDocument {
  type: string;
  status: string;
  uploaded_at?: string;
}

interface KYCStatus {
  kyc_status: string;
  documents: KYCDocument[];
  bank_details?: BankDetails;
}

export default function PartnerKYCPage() {
  const { partner } = usePartnerStore();
  const [kycStatus, setKycStatus] = useState<KYCStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Bank details form
  const [showBankDialog, setShowBankDialog] = useState(false);
  const [bankDetails, setBankDetails] = useState<BankDetails>({
    account_holder_name: '',
    account_number: '',
    ifsc_code: '',
    bank_name: '',
  });

  // Document upload
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [uploadType, setUploadType] = useState<'AADHAAR' | 'PAN' | 'BANK_PROOF'>('AADHAAR');
  const [documentNumber, setDocumentNumber] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchKYCStatus = async () => {
      try {
        const status = await partnerKYCApi.getKYCStatus();
        setKycStatus(status);
        if (status.bank_details) {
          setBankDetails(status.bank_details);
        }
      } catch (error) {
        console.error('Failed to fetch KYC status:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchKYCStatus();
  }, []);

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
      if (!allowedTypes.includes(file.type)) {
        setError('Please upload a valid image (JPG, PNG) or PDF file');
        return;
      }
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setError('File size must be less than 5MB');
        return;
      }
      setSelectedFile(file);
      setError(null);
      // Create preview for images
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onloadend = () => {
          setPreviewUrl(reader.result as string);
        };
        reader.readAsDataURL(file);
      } else {
        setPreviewUrl(null);
      }
    }
  };

  // Clear selected file
  const clearSelectedFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUploadDocument = async () => {
    // Validate mobile number exists
    if (!partner?.phone) {
      setError('Mobile number is required. Please update your profile first.');
      return;
    }

    if (!selectedFile) {
      setError('Please select a document to upload');
      return;
    }

    // Validate document number for Aadhaar and PAN
    if (uploadType === 'AADHAAR' && !documentNumber) {
      setError('Please enter your Aadhaar number');
      return;
    }
    if (uploadType === 'PAN' && !documentNumber) {
      setError('Please enter your PAN number');
      return;
    }

    setError(null);
    setIsSubmitting(true);
    setUploadProgress(0);

    try {
      // Step 1: Upload file to storage
      const uploadResponse = await uploadsApi.uploadImage(selectedFile, 'documents');
      setUploadProgress(50);

      // Step 2: Submit document details with URL
      const response = await partnerKYCApi.uploadDocument({
        document_type: uploadType,
        document_number: documentNumber || undefined,
        document_url: uploadResponse.url,
      });

      setUploadProgress(100);

      if (response.success) {
        setSuccess('Document uploaded successfully!');
        setShowUploadDialog(false);
        setDocumentNumber('');
        clearSelectedFile();

        // Refresh KYC status
        const status = await partnerKYCApi.getKYCStatus();
        setKycStatus(status);
      } else {
        setError(response.message);
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            err.message
          : 'Failed to upload document';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
      setUploadProgress(0);
    }
  };

  const handleUpdateBankDetails = async () => {
    if (!bankDetails.account_holder_name || !bankDetails.account_number || !bankDetails.ifsc_code) {
      setError('Please fill all required fields');
      return;
    }

    setError(null);
    setIsSubmitting(true);

    try {
      const response = await partnerKYCApi.updateBankDetails(bankDetails);

      if (response.success) {
        setSuccess('Bank details updated successfully!');
        setShowBankDialog(false);

        // Refresh KYC status
        const status = await partnerKYCApi.getKYCStatus();
        setKycStatus(status);
      } else {
        setError(response.message);
      }
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail ||
            err.message
          : 'Failed to update bank details';
      setError(errorMessage);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const documents = kycStatus?.documents || [];
  const getDocumentStatus = (type: string) => {
    const doc = documents.find((d) => d.type === type);
    return doc?.status || 'NOT_UPLOADED';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">KYC Verification</h1>
        <p className="text-muted-foreground">
          Complete your KYC to start receiving payouts
        </p>
      </div>

      {success && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">{success}</AlertDescription>
        </Alert>
      )}

      {/* Overall KYC Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Verification Status</CardTitle>
            <Badge className={statusColors[kycStatus?.kyc_status || 'PENDING']?.bg || ''}>
              {statusColors[kycStatus?.kyc_status || 'PENDING']?.icon}
              <span className="ml-1">{kycStatus?.kyc_status || 'PENDING'}</span>
            </Badge>
          </div>
          <CardDescription>
            {kycStatus?.kyc_status === 'VERIFIED'
              ? 'Your account is fully verified. You can now request payouts.'
              : 'Submit all required documents to complete verification.'}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Profile Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Full Name</p>
              <p className="font-medium">{partner?.full_name}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Partner Code</p>
              <p className="font-medium font-mono">{partner?.partner_code}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Mobile</p>
              <p className="font-medium">{partner?.phone}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Email</p>
              <p className="font-medium">{partner?.email || '-'}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Documents Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileCheck className="h-5 w-5" />
            Documents
          </CardTitle>
          <CardDescription>Upload your identity documents for verification</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Aadhaar */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <CreditCard className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">Aadhaar Card</p>
                <p className="text-sm text-muted-foreground">Government issued ID</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={statusColors[getDocumentStatus('AADHAAR')]?.bg || 'bg-gray-100'}>
                {getDocumentStatus('AADHAAR')}
              </Badge>
              {getDocumentStatus('AADHAAR') === 'NOT_UPLOADED' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setUploadType('AADHAAR');
                    setShowUploadDialog(true);
                  }}
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload
                </Button>
              )}
            </div>
          </div>

          {/* PAN */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <CreditCard className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="font-medium">PAN Card</p>
                <p className="text-sm text-muted-foreground">For TDS compliance</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className={statusColors[getDocumentStatus('PAN')]?.bg || 'bg-gray-100'}>
                {getDocumentStatus('PAN')}
              </Badge>
              {getDocumentStatus('PAN') === 'NOT_UPLOADED' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setUploadType('PAN');
                    setShowUploadDialog(true);
                  }}
                >
                  <Upload className="h-4 w-4 mr-1" />
                  Upload
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bank Details */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5" />
                Bank Details
              </CardTitle>
              <CardDescription>Add your bank account for receiving payouts</CardDescription>
            </div>
            <Button variant="outline" onClick={() => setShowBankDialog(true)}>
              {kycStatus?.bank_details ? 'Update' : 'Add'} Bank Details
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {kycStatus?.bank_details ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Account Holder</p>
                <p className="font-medium">{kycStatus.bank_details.account_holder_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Bank Name</p>
                <p className="font-medium">{kycStatus.bank_details.bank_name}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Account Number</p>
                <p className="font-medium font-mono">
                  ****{kycStatus.bank_details.account_number.slice(-4)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">IFSC Code</p>
                <p className="font-medium font-mono">{kycStatus.bank_details.ifsc_code}</p>
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground">No bank details added yet</p>
          )}
        </CardContent>
      </Card>

      {/* Document Upload Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={(open) => {
        setShowUploadDialog(open);
        if (!open) {
          clearSelectedFile();
          setDocumentNumber('');
          setError(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Upload {uploadType === 'AADHAAR' ? 'Aadhaar Card' : uploadType === 'PAN' ? 'PAN Card' : 'Bank Proof'}</DialogTitle>
            <DialogDescription>
              Upload a clear image (JPG, PNG) or PDF of your document
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Mobile Number Check */}
            {!partner?.phone && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Mobile number is required. Please update your profile first.
                </AlertDescription>
              </Alert>
            )}

            {uploadType !== 'BANK_PROOF' && (
              <div className="space-y-2">
                <Label htmlFor="docNumber">
                  {uploadType === 'AADHAAR' ? 'Aadhaar Number *' : 'PAN Number *'}
                </Label>
                <Input
                  id="docNumber"
                  placeholder={
                    uploadType === 'AADHAAR' ? '1234 5678 9012' : 'ABCDE1234F'
                  }
                  value={documentNumber}
                  onChange={(e) => setDocumentNumber(e.target.value)}
                  maxLength={uploadType === 'AADHAAR' ? 14 : 10}
                />
              </div>
            )}

            {/* File Upload Area */}
            <div className="space-y-2">
              <Label>Upload Document *</Label>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/jpg,application/pdf"
                onChange={handleFileSelect}
                className="hidden"
                id="document-upload"
              />

              {!selectedFile ? (
                <label
                  htmlFor="document-upload"
                  className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer bg-muted/50 hover:bg-muted transition-colors"
                >
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <Upload className="w-8 h-8 mb-2 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">
                      <span className="font-semibold">Click to upload</span> or drag and drop
                    </p>
                    <p className="text-xs text-muted-foreground">
                      JPG, PNG or PDF (max 5MB)
                    </p>
                  </div>
                </label>
              ) : (
                <div className="relative border rounded-lg p-4">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="absolute top-2 right-2 h-6 w-6"
                    onClick={clearSelectedFile}
                  >
                    <X className="h-4 w-4" />
                  </Button>

                  {previewUrl ? (
                    <div className="flex items-center gap-4">
                      <img
                        src={previewUrl}
                        alt="Preview"
                        className="w-20 h-20 object-cover rounded"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(selectedFile.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-4">
                      <div className="p-3 bg-primary/10 rounded">
                        <FileImage className="h-6 w-6 text-primary" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {(selectedFile.size / 1024).toFixed(1)} KB • PDF
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Upload Progress */}
            {isSubmitting && uploadProgress > 0 && (
              <div className="space-y-2">
                <Progress value={uploadProgress} className="h-2" />
                <p className="text-xs text-center text-muted-foreground">
                  Uploading... {uploadProgress}%
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadDialog(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button
              onClick={handleUploadDocument}
              disabled={isSubmitting || !selectedFile || !partner?.phone}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload Document
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bank Details Dialog */}
      <Dialog open={showBankDialog} onOpenChange={setShowBankDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bank Details</DialogTitle>
            <DialogDescription>
              Add your bank account details for receiving payouts
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="holderName">Account Holder Name *</Label>
              <Input
                id="holderName"
                placeholder="As per bank records"
                value={bankDetails.account_holder_name}
                onChange={(e) =>
                  setBankDetails({ ...bankDetails, account_holder_name: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="accountNumber">Account Number *</Label>
              <Input
                id="accountNumber"
                placeholder="Enter account number"
                value={bankDetails.account_number}
                onChange={(e) =>
                  setBankDetails({ ...bankDetails, account_number: e.target.value })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="ifsc">IFSC Code *</Label>
              <Input
                id="ifsc"
                placeholder="e.g., SBIN0001234"
                value={bankDetails.ifsc_code}
                onChange={(e) =>
                  setBankDetails({ ...bankDetails, ifsc_code: e.target.value.toUpperCase() })
                }
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="bankName">Bank Name</Label>
              <Input
                id="bankName"
                placeholder="e.g., State Bank of India"
                value={bankDetails.bank_name}
                onChange={(e) => setBankDetails({ ...bankDetails, bank_name: e.target.value })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowBankDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateBankDetails} disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Saving...
                </>
              ) : (
                'Save Bank Details'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
