'use client';

import { useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { format } from 'date-fns';
import {
  ArrowLeft,
  Edit,
  Save,
  X,
  User,
  Building2,
  CreditCard,
  FileText,
  Calendar,
  Clock,
  Mail,
  Phone,
  MapPin,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { hrApi, Employee, SalaryStructure, AttendanceRecord, LeaveRequest, Payslip } from '@/lib/api';

const employmentTypes = [
  { value: 'FULL_TIME', label: 'Full Time' },
  { value: 'PART_TIME', label: 'Part Time' },
  { value: 'CONTRACT', label: 'Contract' },
  { value: 'INTERN', label: 'Intern' },
  { value: 'CONSULTANT', label: 'Consultant' },
];

const employeeStatuses = [
  { value: 'ACTIVE', label: 'Active', variant: 'default' as const },
  { value: 'ON_NOTICE', label: 'On Notice', variant: 'secondary' as const },
  { value: 'ON_LEAVE', label: 'On Leave', variant: 'outline' as const },
  { value: 'SUSPENDED', label: 'Suspended', variant: 'destructive' as const },
  { value: 'RESIGNED', label: 'Resigned', variant: 'secondary' as const },
  { value: 'TERMINATED', label: 'Terminated', variant: 'destructive' as const },
];

function getStatusBadge(status: string) {
  const config = employeeStatuses.find((s) => s.value === status);
  return <Badge variant={config?.variant || 'outline'}>{config?.label || status}</Badge>;
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(value);
}

export default function EmployeeDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const queryClient = useQueryClient();

  const employeeId = params.id as string;
  const isEditMode = searchParams.get('edit') === 'true';

  const [editMode, setEditMode] = useState(isEditMode);
  const [salaryEditMode, setSalaryEditMode] = useState(false);

  const { data: employee, isLoading } = useQuery({
    queryKey: ['employee', employeeId],
    queryFn: () => hrApi.employees.getById(employeeId),
  });

  const { data: salary } = useQuery({
    queryKey: ['employee-salary', employeeId],
    queryFn: () => hrApi.employees.getSalary(employeeId),
    retry: false,
  });

  const { data: attendanceData } = useQuery({
    queryKey: ['employee-attendance', employeeId],
    queryFn: () => hrApi.attendance.list({ employee_id: employeeId, page: 1, size: 30 }),
  });

  const { data: leavesData } = useQuery({
    queryKey: ['employee-leaves', employeeId],
    queryFn: () => hrApi.leave.listRequests({ employee_id: employeeId, page: 1, size: 20 }),
  });

  const { data: payslipsData } = useQuery({
    queryKey: ['employee-payslips', employeeId],
    queryFn: () => hrApi.payroll.listPayslips({ employee_id: employeeId, page: 1, size: 20 }),
  });

  const { data: departments } = useQuery({
    queryKey: ['departments-dropdown'],
    queryFn: hrApi.departments.dropdown,
  });

  const { data: employeesDropdown } = useQuery({
    queryKey: ['employees-dropdown'],
    queryFn: () => hrApi.employees.dropdown(),
  });

  const [formData, setFormData] = useState<Partial<Employee>>({});
  const [salaryFormData, setSalaryFormData] = useState<Partial<SalaryStructure>>({});

  // Initialize form when employee data loads
  useState(() => {
    if (employee) {
      setFormData(employee);
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: Partial<Employee>) => hrApi.employees.update(employeeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employee', employeeId] });
      setEditMode(false);
      toast.success('Employee updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error updating employee');
    },
  });

  const updateSalaryMutation = useMutation({
    mutationFn: (data: Parameters<typeof hrApi.employees.updateSalary>[1]) =>
      hrApi.employees.updateSalary(employeeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employee-salary', employeeId] });
      setSalaryEditMode(false);
      toast.success('Salary updated successfully');
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Error updating salary');
    },
  });

  const handleStartEdit = () => {
    if (employee) {
      setFormData({ ...employee });
      setEditMode(true);
    }
  };

  const handleCancelEdit = () => {
    setEditMode(false);
    setFormData({});
  };

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

  const handleStartSalaryEdit = () => {
    if (salary) {
      setSalaryFormData({ ...salary });
    } else {
      setSalaryFormData({
        basic_salary: 0,
        hra: 0,
        conveyance: 0,
        medical_allowance: 0,
        special_allowance: 0,
        other_allowances: 0,
        pf_applicable: true,
        esic_applicable: false,
        pt_applicable: true,
      });
    }
    setSalaryEditMode(true);
  };

  const handleSaveSalary = () => {
    updateSalaryMutation.mutate({
      employee_id: employeeId,
      effective_from: format(new Date(), 'yyyy-MM-dd'),
      basic_salary: salaryFormData.basic_salary || 0,
      hra: salaryFormData.hra,
      conveyance: salaryFormData.conveyance,
      medical_allowance: salaryFormData.medical_allowance,
      special_allowance: salaryFormData.special_allowance,
      other_allowances: salaryFormData.other_allowances,
      pf_applicable: salaryFormData.pf_applicable,
      esic_applicable: salaryFormData.esic_applicable,
      pt_applicable: salaryFormData.pt_applicable,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32 mt-2" />
          </div>
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!employee) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
        <h2 className="text-xl font-semibold">Employee Not Found</h2>
        <p className="text-muted-foreground">The employee you are looking for does not exist.</p>
        <Button className="mt-4" asChild>
          <Link href="/dashboard/hr/employees">Back to Employees</Link>
        </Button>
      </div>
    );
  }

  const attendance = attendanceData?.items || [];
  const leaves = leavesData?.items || [];
  const payslips = payslipsData?.items || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="icon" asChild>
            <Link href="/dashboard/hr/employees">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <Avatar className="h-16 w-16">
            <AvatarImage src={employee.avatar_url || undefined} />
            <AvatarFallback className="text-lg">
              {employee.first_name?.[0]}{employee.last_name?.[0]}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{employee.full_name}</h1>
              {getStatusBadge(employee.status)}
            </div>
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <span>{employee.employee_code}</span>
              {employee.designation && (
                <>
                  <span>|</span>
                  <span>{employee.designation}</span>
                </>
              )}
              {employee.department_name && (
                <>
                  <span>|</span>
                  <span>{employee.department_name}</span>
                </>
              )}
            </div>
          </div>
        </div>
        {!editMode ? (
          <Button onClick={handleStartEdit}>
            <Edit className="mr-2 h-4 w-4" />
            Edit
          </Button>
        ) : (
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCancelEdit}>
              <X className="mr-2 h-4 w-4" />
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateMutation.isPending ? 'Saving...' : 'Save'}
            </Button>
          </div>
        )}
      </div>

      {/* Content Tabs */}
      <Tabs defaultValue="personal" className="space-y-6">
        <TabsList>
          <TabsTrigger value="personal">
            <User className="mr-2 h-4 w-4" />
            Personal
          </TabsTrigger>
          <TabsTrigger value="employment">
            <Building2 className="mr-2 h-4 w-4" />
            Employment
          </TabsTrigger>
          <TabsTrigger value="salary">
            <CreditCard className="mr-2 h-4 w-4" />
            Salary
          </TabsTrigger>
          <TabsTrigger value="attendance">
            <Calendar className="mr-2 h-4 w-4" />
            Attendance
          </TabsTrigger>
          <TabsTrigger value="leaves">
            <Clock className="mr-2 h-4 w-4" />
            Leaves
          </TabsTrigger>
          <TabsTrigger value="payslips">
            <FileText className="mr-2 h-4 w-4" />
            Payslips
          </TabsTrigger>
        </TabsList>

        {/* Personal Tab */}
        <TabsContent value="personal" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-muted-foreground" />
                <div>
                  <div className="text-sm text-muted-foreground">Email</div>
                  <div>{employee.email}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-muted-foreground" />
                <div>
                  <div className="text-sm text-muted-foreground">Phone</div>
                  <div>{employee.phone || '-'}</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Phone className="h-5 w-5 text-muted-foreground" />
                <div>
                  <div className="text-sm text-muted-foreground">Personal Phone</div>
                  <div>{employee.personal_phone || '-'}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Personal Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-4">
              <div>
                <div className="text-sm text-muted-foreground">Date of Birth</div>
                <div>{employee.date_of_birth ? format(new Date(employee.date_of_birth), 'dd MMM yyyy') : '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Gender</div>
                <div>{employee.gender || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Blood Group</div>
                <div>{employee.blood_group || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Marital Status</div>
                <div>{employee.marital_status || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Nationality</div>
                <div>{employee.nationality || 'Indian'}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Emergency Contact</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-sm text-muted-foreground">Name</div>
                <div>{employee.emergency_contact_name || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Phone</div>
                <div>{employee.emergency_contact_phone || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Relation</div>
                <div>{employee.emergency_contact_relation || '-'}</div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Documents</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-4">
              <div>
                <div className="text-sm text-muted-foreground">PAN Number</div>
                <div className="font-mono">{employee.pan_number || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Aadhaar Number</div>
                <div className="font-mono">{employee.aadhaar_number || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">UAN (PF)</div>
                <div className="font-mono">{employee.uan_number || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">ESIC Number</div>
                <div className="font-mono">{employee.esic_number || '-'}</div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Employment Tab */}
        <TabsContent value="employment" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Employment Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              {editMode ? (
                <>
                  <div className="grid gap-2">
                    <Label>Department</Label>
                    <Select
                      value={formData.department_id || ''}
                      onValueChange={(v) => setFormData({ ...formData, department_id: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        {departments?.map((d) => (
                          <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Designation</Label>
                    <Input
                      value={formData.designation || ''}
                      onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label>Employment Type</Label>
                    <Select
                      value={formData.employment_type || ''}
                      onValueChange={(v) => setFormData({ ...formData, employment_type: v })}
                    >
                      <SelectTrigger>
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
                    <Label>Status</Label>
                    <Select
                      value={formData.status || ''}
                      onValueChange={(v) => setFormData({ ...formData, status: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                      <SelectContent>
                        {employeeStatuses.map((s) => (
                          <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="grid gap-2">
                    <Label>Reporting Manager</Label>
                    <Select
                      value={formData.reporting_manager_id || ''}
                      onValueChange={(v) => setFormData({ ...formData, reporting_manager_id: v })}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select manager" />
                      </SelectTrigger>
                      <SelectContent>
                        {employeesDropdown?.filter(e => e.id !== employeeId).map((e) => (
                          <SelectItem key={e.id} value={e.id}>{e.full_name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <div className="text-sm text-muted-foreground">Department</div>
                    <div>{employee.department_name || '-'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Designation</div>
                    <div>{employee.designation || '-'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Employment Type</div>
                    <div>{employmentTypes.find(et => et.value === employee.employment_type)?.label || employee.employment_type}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Joining Date</div>
                    <div>{employee.joining_date ? format(new Date(employee.joining_date), 'dd MMM yyyy') : '-'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Confirmation Date</div>
                    <div>{employee.confirmation_date ? format(new Date(employee.confirmation_date), 'dd MMM yyyy') : '-'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Reporting Manager</div>
                    <div>{employee.reporting_manager_name || '-'}</div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Bank Details</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-3">
              <div>
                <div className="text-sm text-muted-foreground">Bank Name</div>
                <div>{employee.bank_name || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Account Number</div>
                <div className="font-mono">{employee.bank_account_number || '-'}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">IFSC Code</div>
                <div className="font-mono">{employee.bank_ifsc_code || '-'}</div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Salary Tab */}
        <TabsContent value="salary" className="space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Salary Structure</CardTitle>
                <CardDescription>
                  {salary?.effective_from ? `Effective from ${format(new Date(salary.effective_from), 'dd MMM yyyy')}` : 'Not configured'}
                </CardDescription>
              </div>
              {!salaryEditMode ? (
                <Button variant="outline" onClick={handleStartSalaryEdit}>
                  <Edit className="mr-2 h-4 w-4" />
                  {salary ? 'Edit' : 'Configure'}
                </Button>
              ) : (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={() => setSalaryEditMode(false)}>Cancel</Button>
                  <Button onClick={handleSaveSalary} disabled={updateSalaryMutation.isPending}>
                    {updateSalaryMutation.isPending ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              )}
            </CardHeader>
            <CardContent>
              {salaryEditMode ? (
                <div className="grid gap-6">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="grid gap-2">
                      <Label>Basic Salary</Label>
                      <Input
                        type="number"
                        value={salaryFormData.basic_salary || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, basic_salary: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>HRA</Label>
                      <Input
                        type="number"
                        value={salaryFormData.hra || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, hra: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>Conveyance</Label>
                      <Input
                        type="number"
                        value={salaryFormData.conveyance || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, conveyance: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>Medical Allowance</Label>
                      <Input
                        type="number"
                        value={salaryFormData.medical_allowance || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, medical_allowance: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>Special Allowance</Label>
                      <Input
                        type="number"
                        value={salaryFormData.special_allowance || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, special_allowance: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label>Other Allowances</Label>
                      <Input
                        type="number"
                        value={salaryFormData.other_allowances || 0}
                        onChange={(e) => setSalaryFormData({ ...salaryFormData, other_allowances: parseFloat(e.target.value) || 0 })}
                      />
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={salaryFormData.pf_applicable}
                        onCheckedChange={(v) => setSalaryFormData({ ...salaryFormData, pf_applicable: v })}
                      />
                      <Label>PF Applicable</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={salaryFormData.esic_applicable}
                        onCheckedChange={(v) => setSalaryFormData({ ...salaryFormData, esic_applicable: v })}
                      />
                      <Label>ESIC Applicable</Label>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={salaryFormData.pt_applicable}
                        onCheckedChange={(v) => setSalaryFormData({ ...salaryFormData, pt_applicable: v })}
                      />
                      <Label>PT Applicable</Label>
                    </div>
                  </div>
                </div>
              ) : salary ? (
                <div className="grid gap-6">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <h4 className="font-medium mb-3">Earnings</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Basic Salary</span>
                          <span>{formatCurrency(salary.basic_salary)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">HRA</span>
                          <span>{formatCurrency(salary.hra)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Conveyance</span>
                          <span>{formatCurrency(salary.conveyance)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Medical Allowance</span>
                          <span>{formatCurrency(salary.medical_allowance)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Special Allowance</span>
                          <span>{formatCurrency(salary.special_allowance)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Other Allowances</span>
                          <span>{formatCurrency(salary.other_allowances)}</span>
                        </div>
                        <div className="flex justify-between border-t pt-2 font-medium">
                          <span>Gross Salary</span>
                          <span>{formatCurrency(salary.gross_salary)}</span>
                        </div>
                      </div>
                    </div>
                    <div>
                      <h4 className="font-medium mb-3">Statutory Compliance</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">PF (Employer)</span>
                          <span>{formatCurrency(salary.employer_pf)}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">ESIC (Employer)</span>
                          <span>{formatCurrency(salary.employer_esic)}</span>
                        </div>
                        <div className="flex justify-between border-t pt-2 font-medium">
                          <span>Monthly CTC</span>
                          <span>{formatCurrency(salary.monthly_ctc)}</span>
                        </div>
                        <div className="flex justify-between font-medium">
                          <span>Annual CTC</span>
                          <span>{formatCurrency(salary.annual_ctc)}</span>
                        </div>
                      </div>
                      <div className="mt-4 flex gap-4">
                        <Badge variant={salary.pf_applicable ? 'default' : 'secondary'}>
                          PF {salary.pf_applicable ? 'Yes' : 'No'}
                        </Badge>
                        <Badge variant={salary.esic_applicable ? 'default' : 'secondary'}>
                          ESIC {salary.esic_applicable ? 'Yes' : 'No'}
                        </Badge>
                        <Badge variant={salary.pt_applicable ? 'default' : 'secondary'}>
                          PT {salary.pt_applicable ? 'Yes' : 'No'}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <CreditCard className="h-12 w-12 mx-auto mb-4" />
                  <p>No salary structure configured</p>
                  <p className="text-sm">Click Configure to set up salary details</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Attendance Tab */}
        <TabsContent value="attendance">
          <Card>
            <CardHeader>
              <CardTitle>Recent Attendance</CardTitle>
              <CardDescription>Last 30 days attendance records</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Check In</TableHead>
                    <TableHead>Check Out</TableHead>
                    <TableHead>Work Hours</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Remarks</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attendance.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                        No attendance records found
                      </TableCell>
                    </TableRow>
                  ) : (
                    attendance.map((record: AttendanceRecord) => (
                      <TableRow key={record.id}>
                        <TableCell>{record.attendance_date ? format(new Date(record.attendance_date), 'dd MMM yyyy') : '-'}</TableCell>
                        <TableCell>
                          {record.check_in ? format(new Date(record.check_in), 'hh:mm a') : '-'}
                        </TableCell>
                        <TableCell>
                          {record.check_out ? format(new Date(record.check_out), 'hh:mm a') : '-'}
                        </TableCell>
                        <TableCell>{record.work_hours ? `${record.work_hours.toFixed(1)} hrs` : '-'}</TableCell>
                        <TableCell>
                          <Badge variant={record.status === 'PRESENT' ? 'default' : 'secondary'}>
                            {record.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="max-w-[150px] truncate">{record.remarks || '-'}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Leaves Tab */}
        <TabsContent value="leaves">
          <Card>
            <CardHeader>
              <CardTitle>Leave History</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>From</TableHead>
                    <TableHead>To</TableHead>
                    <TableHead>Days</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Applied On</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leaves.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No leave records found
                      </TableCell>
                    </TableRow>
                  ) : (
                    leaves.map((leave: LeaveRequest) => (
                      <TableRow key={leave.id}>
                        <TableCell>
                          <Badge variant="outline">{leave.leave_type}</Badge>
                        </TableCell>
                        <TableCell>{leave.from_date ? format(new Date(leave.from_date), 'dd MMM yyyy') : '-'}</TableCell>
                        <TableCell>{leave.to_date ? format(new Date(leave.to_date), 'dd MMM yyyy') : '-'}</TableCell>
                        <TableCell>{leave.days}</TableCell>
                        <TableCell className="max-w-[150px] truncate">{leave.reason || '-'}</TableCell>
                        <TableCell>
                          <Badge variant={
                            leave.status === 'APPROVED' ? 'default' :
                            leave.status === 'REJECTED' ? 'destructive' : 'secondary'
                          }>
                            {leave.status}
                          </Badge>
                        </TableCell>
                        <TableCell>{leave.applied_on ? format(new Date(leave.applied_on), 'dd MMM yyyy') : '-'}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Payslips Tab */}
        <TabsContent value="payslips">
          <Card>
            <CardHeader>
              <CardTitle>Payslips</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Payslip #</TableHead>
                    <TableHead>Month</TableHead>
                    <TableHead>Working Days</TableHead>
                    <TableHead>Gross</TableHead>
                    <TableHead>Deductions</TableHead>
                    <TableHead>Net Pay</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {payslips.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No payslips found
                      </TableCell>
                    </TableRow>
                  ) : (
                    payslips.map((payslip: Payslip) => (
                      <TableRow key={payslip.id}>
                        <TableCell className="font-mono">{payslip.payslip_number}</TableCell>
                        <TableCell>{payslip.created_at ? format(new Date(payslip.created_at), 'MMM yyyy') : '-'}</TableCell>
                        <TableCell>{payslip.days_present}/{payslip.working_days}</TableCell>
                        <TableCell>{formatCurrency(payslip.gross_earnings)}</TableCell>
                        <TableCell className="text-red-600">-{formatCurrency(payslip.total_deductions)}</TableCell>
                        <TableCell className="font-medium text-green-600">{formatCurrency(payslip.net_salary)}</TableCell>
                        <TableCell>
                          {payslip.payslip_pdf_url && (
                            <Button variant="ghost" size="sm" asChild>
                              <a href={payslip.payslip_pdf_url} target="_blank" rel="noopener noreferrer">
                                <FileText className="h-4 w-4" />
                              </a>
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
