'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import Link from 'next/link';
import {
  ArrowLeft,
  Save,
  User,
  Building2,
  CreditCard,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import { hrApi, rolesApi } from '@/lib/api';

const employmentTypes = [
  { value: 'FULL_TIME', label: 'Full Time' },
  { value: 'PART_TIME', label: 'Part Time' },
  { value: 'CONTRACT', label: 'Contract' },
  { value: 'INTERN', label: 'Intern' },
  { value: 'CONSULTANT', label: 'Consultant' },
];

const genders = [
  { value: 'MALE', label: 'Male' },
  { value: 'FEMALE', label: 'Female' },
  { value: 'OTHER', label: 'Other' },
];

const bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];

const maritalStatuses = [
  { value: 'SINGLE', label: 'Single' },
  { value: 'MARRIED', label: 'Married' },
  { value: 'DIVORCED', label: 'Divorced' },
  { value: 'WIDOWED', label: 'Widowed' },
];

interface AddressForm {
  line1: string;
  line2: string;
  city: string;
  state: string;
  pincode: string;
  country: string;
}

const defaultAddress: AddressForm = {
  line1: '',
  line2: '',
  city: '',
  state: '',
  pincode: '',
  country: 'India',
};

export default function NewEmployeePage() {
  const router = useRouter();

  const [formData, setFormData] = useState({
    // User Account
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    phone: '',
    role_ids: [] as string[],

    // Personal Info
    date_of_birth: '',
    gender: '',
    blood_group: '',
    marital_status: '',
    nationality: 'Indian',
    personal_email: '',
    personal_phone: '',

    // Emergency Contact
    emergency_contact_name: '',
    emergency_contact_phone: '',
    emergency_contact_relation: '',

    // Employment
    department_id: '',
    designation: '',
    employment_type: 'FULL_TIME',
    joining_date: '',
    confirmation_date: '',
    reporting_manager_id: '',

    // Documents (Indian)
    pan_number: '',
    aadhaar_number: '',
    uan_number: '',
    esic_number: '',

    // Bank Details
    bank_name: '',
    bank_account_number: '',
    bank_ifsc_code: '',
  });

  const [currentAddress, setCurrentAddress] = useState<AddressForm>(defaultAddress);
  const [permanentAddress, setPermanentAddress] = useState<AddressForm>(defaultAddress);
  const [sameAsCurrentAddress, setSameAsCurrentAddress] = useState(false);

  const { data: departments } = useQuery({
    queryKey: ['departments-dropdown'],
    queryFn: hrApi.departments.dropdown,
  });

  const { data: employees } = useQuery({
    queryKey: ['employees-dropdown'],
    queryFn: () => hrApi.employees.dropdown(),
  });

  const { data: rolesData } = useQuery({
    queryKey: ['roles'],
    queryFn: () => rolesApi.list({ page: 1, size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: hrApi.employees.create,
    onSuccess: (employee) => {
      toast.success('Employee created successfully');
      router.push(`/dashboard/hr/employees/${employee.id}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error creating employee');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.email || !formData.password || !formData.first_name || !formData.joining_date) {
      toast.error('Please fill in all required fields (Email, Password, First Name, Joining Date)');
      return;
    }

    const finalPermanentAddress = sameAsCurrentAddress ? currentAddress : permanentAddress;

    createMutation.mutate({
      ...formData,
      current_address: currentAddress as unknown as Record<string, unknown>,
      permanent_address: finalPermanentAddress as unknown as Record<string, unknown>,
    });
  };

  const updateField = (field: string, value: string | string[]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/hr/employees">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Add Employee</h1>
            <p className="text-muted-foreground">Create a new employee with user account</p>
          </div>
        </div>
        <Button onClick={handleSubmit} disabled={createMutation.isPending}>
          <Save className="mr-2 h-4 w-4" />
          {createMutation.isPending ? 'Creating...' : 'Create Employee'}
        </Button>
      </div>

      <form onSubmit={handleSubmit}>
        <Tabs defaultValue="personal" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:w-auto lg:inline-grid">
            <TabsTrigger value="personal">
              <User className="mr-2 h-4 w-4" />
              Personal
            </TabsTrigger>
            <TabsTrigger value="employment">
              <Building2 className="mr-2 h-4 w-4" />
              Employment
            </TabsTrigger>
            <TabsTrigger value="documents">
              <FileText className="mr-2 h-4 w-4" />
              Documents
            </TabsTrigger>
            <TabsTrigger value="bank">
              <CreditCard className="mr-2 h-4 w-4" />
              Bank & Salary
            </TabsTrigger>
          </TabsList>

          {/* Personal Info Tab */}
          <TabsContent value="personal" className="space-y-6">
            {/* User Account */}
            <Card>
              <CardHeader>
                <CardTitle>User Account</CardTitle>
                <CardDescription>Login credentials for ERP access</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="email">Email *</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="employee@company.com"
                    value={formData.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="password">Password *</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min 8 characters"
                    value={formData.password}
                    onChange={(e) => updateField('password', e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="phone">Phone</Label>
                  <Input
                    id="phone"
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={formData.phone}
                    onChange={(e) => updateField('phone', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Personal Details */}
            <Card>
              <CardHeader>
                <CardTitle>Personal Details</CardTitle>
                <CardDescription>Basic personal information</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="first_name">First Name *</Label>
                  <Input
                    id="first_name"
                    placeholder="John"
                    value={formData.first_name}
                    onChange={(e) => updateField('first_name', e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="last_name">Last Name</Label>
                  <Input
                    id="last_name"
                    placeholder="Doe"
                    value={formData.last_name}
                    onChange={(e) => updateField('last_name', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="date_of_birth">Date of Birth</Label>
                  <Input
                    id="date_of_birth"
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => updateField('date_of_birth', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="gender">Gender</Label>
                  <Select value={formData.gender} onValueChange={(v) => updateField('gender', v)}>
                    <SelectTrigger id="gender">
                      <SelectValue placeholder="Select gender" />
                    </SelectTrigger>
                    <SelectContent>
                      {genders.map((g) => (
                        <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="blood_group">Blood Group</Label>
                  <Select value={formData.blood_group} onValueChange={(v) => updateField('blood_group', v)}>
                    <SelectTrigger id="blood_group">
                      <SelectValue placeholder="Select blood group" />
                    </SelectTrigger>
                    <SelectContent>
                      {bloodGroups.map((bg) => (
                        <SelectItem key={bg} value={bg}>{bg}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="marital_status">Marital Status</Label>
                  <Select value={formData.marital_status} onValueChange={(v) => updateField('marital_status', v)}>
                    <SelectTrigger id="marital_status">
                      <SelectValue placeholder="Select status" />
                    </SelectTrigger>
                    <SelectContent>
                      {maritalStatuses.map((ms) => (
                        <SelectItem key={ms.value} value={ms.value}>{ms.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="nationality">Nationality</Label>
                  <Input
                    id="nationality"
                    value={formData.nationality}
                    onChange={(e) => updateField('nationality', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="personal_email">Personal Email</Label>
                  <Input
                    id="personal_email"
                    type="email"
                    placeholder="personal@email.com"
                    value={formData.personal_email}
                    onChange={(e) => updateField('personal_email', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="personal_phone">Personal Phone</Label>
                  <Input
                    id="personal_phone"
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={formData.personal_phone}
                    onChange={(e) => updateField('personal_phone', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Emergency Contact */}
            <Card>
              <CardHeader>
                <CardTitle>Emergency Contact</CardTitle>
                <CardDescription>Contact in case of emergency</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="emergency_contact_name">Contact Name</Label>
                  <Input
                    id="emergency_contact_name"
                    placeholder="Name"
                    value={formData.emergency_contact_name}
                    onChange={(e) => updateField('emergency_contact_name', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="emergency_contact_phone">Contact Phone</Label>
                  <Input
                    id="emergency_contact_phone"
                    type="tel"
                    placeholder="+91 XXXXX XXXXX"
                    value={formData.emergency_contact_phone}
                    onChange={(e) => updateField('emergency_contact_phone', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="emergency_contact_relation">Relation</Label>
                  <Input
                    id="emergency_contact_relation"
                    placeholder="Father, Spouse, etc."
                    value={formData.emergency_contact_relation}
                    onChange={(e) => updateField('emergency_contact_relation', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Current Address */}
            <Card>
              <CardHeader>
                <CardTitle>Current Address</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2 md:col-span-2">
                  <Label>Address Line 1</Label>
                  <Input
                    placeholder="Street address"
                    value={currentAddress.line1}
                    onChange={(e) => setCurrentAddress({ ...currentAddress, line1: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Address Line 2</Label>
                  <Input
                    placeholder="Apartment, suite, etc."
                    value={currentAddress.line2}
                    onChange={(e) => setCurrentAddress({ ...currentAddress, line2: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label>City</Label>
                  <Input
                    placeholder="City"
                    value={currentAddress.city}
                    onChange={(e) => setCurrentAddress({ ...currentAddress, city: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label>State</Label>
                  <Input
                    placeholder="State"
                    value={currentAddress.state}
                    onChange={(e) => setCurrentAddress({ ...currentAddress, state: e.target.value })}
                  />
                </div>
                <div className="grid gap-2">
                  <Label>Pincode</Label>
                  <Input
                    placeholder="Pincode"
                    value={currentAddress.pincode}
                    onChange={(e) => setCurrentAddress({ ...currentAddress, pincode: e.target.value })}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Permanent Address */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-4">
                  Permanent Address
                  <label className="flex items-center gap-2 text-sm font-normal">
                    <input
                      type="checkbox"
                      checked={sameAsCurrentAddress}
                      onChange={(e) => setSameAsCurrentAddress(e.target.checked)}
                      className="rounded"
                    />
                    Same as current address
                  </label>
                </CardTitle>
              </CardHeader>
              {!sameAsCurrentAddress && (
                <CardContent className="grid gap-4 md:grid-cols-3">
                  <div className="grid gap-2 md:col-span-2">
                    <Label>Address Line 1</Label>
                    <Input
                      placeholder="Street address"
                      value={permanentAddress.line1}
                      onChange={(e) => setPermanentAddress({ ...permanentAddress, line1: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>Address Line 2</Label>
                    <Input
                      placeholder="Apartment, suite, etc."
                      value={permanentAddress.line2}
                      onChange={(e) => setPermanentAddress({ ...permanentAddress, line2: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>City</Label>
                    <Input
                      placeholder="City"
                      value={permanentAddress.city}
                      onChange={(e) => setPermanentAddress({ ...permanentAddress, city: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>State</Label>
                    <Input
                      placeholder="State"
                      value={permanentAddress.state}
                      onChange={(e) => setPermanentAddress({ ...permanentAddress, state: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>Pincode</Label>
                    <Input
                      placeholder="Pincode"
                      value={permanentAddress.pincode}
                      onChange={(e) => setPermanentAddress({ ...permanentAddress, pincode: e.target.value })}
                    />
                  </div>
                </CardContent>
              )}
            </Card>
          </TabsContent>

          {/* Employment Tab */}
          <TabsContent value="employment" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Employment Details</CardTitle>
                <CardDescription>Job-related information</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="department_id">Department</Label>
                  <Select value={formData.department_id} onValueChange={(v) => updateField('department_id', v)}>
                    <SelectTrigger id="department_id">
                      <SelectValue placeholder="Select department" />
                    </SelectTrigger>
                    <SelectContent>
                      {departments?.map((dept) => (
                        <SelectItem key={dept.id} value={dept.id}>{dept.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="designation">Designation</Label>
                  <Input
                    id="designation"
                    placeholder="Software Engineer"
                    value={formData.designation}
                    onChange={(e) => updateField('designation', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="employment_type">Employment Type</Label>
                  <Select value={formData.employment_type} onValueChange={(v) => updateField('employment_type', v)}>
                    <SelectTrigger id="employment_type">
                      <SelectValue placeholder="Select type" />
                    </SelectTrigger>
                    <SelectContent>
                      {employmentTypes.map((et) => (
                        <SelectItem key={et.value} value={et.value}>{et.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="joining_date">Joining Date *</Label>
                  <Input
                    id="joining_date"
                    type="date"
                    value={formData.joining_date}
                    onChange={(e) => updateField('joining_date', e.target.value)}
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="confirmation_date">Confirmation Date</Label>
                  <Input
                    id="confirmation_date"
                    type="date"
                    value={formData.confirmation_date}
                    onChange={(e) => updateField('confirmation_date', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="reporting_manager_id">Reporting Manager</Label>
                  <Select value={formData.reporting_manager_id} onValueChange={(v) => updateField('reporting_manager_id', v)}>
                    <SelectTrigger id="reporting_manager_id">
                      <SelectValue placeholder="Select manager" />
                    </SelectTrigger>
                    <SelectContent>
                      {employees?.map((emp) => (
                        <SelectItem key={emp.id} value={emp.id}>
                          {emp.full_name} ({emp.employee_code})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Roles</CardTitle>
                <CardDescription>ERP access roles for this employee</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2">
                  <Label>Assign Roles</Label>
                  <div className="grid gap-2 md:grid-cols-3 lg:grid-cols-4">
                    {rolesData?.items?.map((role) => (
                      <label key={role.id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={formData.role_ids.includes(role.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              updateField('role_ids', [...formData.role_ids, role.id]);
                            } else {
                              updateField('role_ids', formData.role_ids.filter((id) => id !== role.id));
                            }
                          }}
                          className="rounded"
                        />
                        {role.name}
                      </label>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Documents Tab */}
          <TabsContent value="documents" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Identity Documents</CardTitle>
                <CardDescription>Indian statutory documents</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="pan_number">PAN Number</Label>
                  <Input
                    id="pan_number"
                    placeholder="ABCDE1234F"
                    maxLength={10}
                    value={formData.pan_number}
                    onChange={(e) => updateField('pan_number', e.target.value.toUpperCase())}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="aadhaar_number">Aadhaar Number</Label>
                  <Input
                    id="aadhaar_number"
                    placeholder="XXXX XXXX XXXX"
                    maxLength={12}
                    value={formData.aadhaar_number}
                    onChange={(e) => updateField('aadhaar_number', e.target.value.replace(/\D/g, ''))}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="uan_number">UAN Number (PF)</Label>
                  <Input
                    id="uan_number"
                    placeholder="Universal Account Number"
                    maxLength={12}
                    value={formData.uan_number}
                    onChange={(e) => updateField('uan_number', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="esic_number">ESIC Number</Label>
                  <Input
                    id="esic_number"
                    placeholder="ESIC IP Number"
                    maxLength={17}
                    value={formData.esic_number}
                    onChange={(e) => updateField('esic_number', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Bank Tab */}
          <TabsContent value="bank" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Bank Account Details</CardTitle>
                <CardDescription>For salary disbursement</CardDescription>
              </CardHeader>
              <CardContent className="grid gap-4 md:grid-cols-3">
                <div className="grid gap-2">
                  <Label htmlFor="bank_name">Bank Name</Label>
                  <Input
                    id="bank_name"
                    placeholder="HDFC Bank"
                    value={formData.bank_name}
                    onChange={(e) => updateField('bank_name', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="bank_account_number">Account Number</Label>
                  <Input
                    id="bank_account_number"
                    placeholder="Account Number"
                    value={formData.bank_account_number}
                    onChange={(e) => updateField('bank_account_number', e.target.value)}
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="bank_ifsc_code">IFSC Code</Label>
                  <Input
                    id="bank_ifsc_code"
                    placeholder="HDFC0001234"
                    maxLength={11}
                    value={formData.bank_ifsc_code}
                    onChange={(e) => updateField('bank_ifsc_code', e.target.value.toUpperCase())}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Salary Structure</CardTitle>
                <CardDescription>
                  Salary details can be configured after creating the employee profile
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  After the employee is created, you can set up their complete salary structure including Basic, HRA, allowances, and statutory deductions (PF, ESIC, Professional Tax).
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </form>
    </div>
  );
}
