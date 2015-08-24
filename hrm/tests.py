import io
from dateutil.relativedelta import relativedelta
from datetime import date, timedelta
from decimal import Decimal
from django.test.testcases import TestCase

from django.core.exceptions import MultipleObjectsReturned

from .models import Hrm, VipMonthly, HrmMonthly, Employee
from .readers import HrmUsageReportReader, VipMonthlyReader, HrmMonthlyReader, EmployeeReader
from hrm.summary import Summarize
from hrm.readers import OpeningBalancesReader


class DummySummarize(Summarize):

    def write(self, data):
        pass


class TestHrm(TestCase):

    opening_balances = (
        'Code Lastname,Firstname,Joined, Balance\n'
        '573,Moraz,Pat, 14/2/11, 18.3\n'
        '153,Bruford,Bill,01/01/04,3.17\n'
        '906,Metheny,Pat,01/10/14,4.17\n'
        '784,Howe,Steve,04/11/13,13.67\n'
    )

    vip_monthly_data = (
        'Employee Code,Employee,Leave Balance\n'
        '573,Mr P Moraz,13.3\n'
        '153,Mr B Bruford,3.17\n'
        '906,Mr P Metheny,4.17\n'
        '784,Mr S Howe,13.67\n'
    )

    hrm_monthly_data = (
        'Date,Employee Name,Leave Type,Number of Days,Status,Comments\n'
        '10/8/15,Patrick Philippe Moraz,Annual Leave,5,Taken(5.0000) ,\n'
        '6/8/15,Bill Bruford,Annual Leave,18,Scheduled(8.0000) Taken(10.0000) ,\n'
        '20/8/15,Pat Metheny,Sick Leave,7,Pending Approval(7.0000) ,\n'
        '31/8/15,Jon  Anderson,Annual Leave,1,Scheduled(1.0000) ,\n'
        '26/8/15,Jon  Anderson,Annual Leave,3,Scheduled(3.0000) ,\n'
        '13/8/15,Steve  Howe,Annual Leave,6,Scheduled(3.0000) ,\n'
        '13/8/15,Steve  Howe,Sick Leave,6,Scheduled(3.0000) ,\n'
        '13/8/15, Tony   Kaye,Annual Leave,6,Scheduled(3.0000) ,\n'
    )

    employee_data = (
        '"Employee Id","Employee Last Name","Employee First Name","Job Title","Employment Status","Joined Date","Sub Unit",Location,"Termination Date"\n'
        '573,Moraz,Patrick,"Study Coordinator-Physician",Contract,2011-02-14,"Mpepu Gaborone",MPEPU,\n'
        '731,White,Alan,DRIVER,Contract,2013-08-12,,"CTU- Molepolole ",2015-03-05\n'
        '0906,Metheny,Pat,,Contract,2014-10-01,Laboratory,"Lab - Gaborone",\n'
        '153,Bruford,Bill,"ACTG Network Si",Contract,2004-01-01,"CTU Gaborone","CTU- Gaborone",\n'
        '644,Anderson,Jon,"Systems Developer / Analyst",Contract,2012-09-01,"Data Management","DMC - Headquarters",\n'
        '55,Squire,Chris,"Office Assistant",Contract,2007-10-01,"Early Infant Treatment","Tshipidi- Gaborone",\n'
        '0784,Howe,Steve,"Recruitment Officer",Contract,2013-11-04,"Mpepu Gaborone",MPEPU,\n'
        '0785, Kaye,Tony  ,"Recruitment Officer",Contract,2013-11-04,"Mpepu Gaborone",MPEPU,\n'
    )

    def load_employees_from_file(self):
        csvfile = '~/source/hrm/data/employee.csv'
        reader = EmployeeReader(csvfile)
        reader.load()

    def load_employees_from_file_object(self):
        csvfile = io.StringIO(self.employee_data)
        reader = EmployeeReader(filename=None, file_object=csvfile)
        reader.load()

    def load_openingbalances_from_file_object(self):
        csvfile = io.StringIO(self.opening_balances)
        reader = OpeningBalancesReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()

    def load_hrm_from_file_object(self):
        csvfile = io.StringIO(self.hrm_monthly_data)
        reader = HrmMonthlyReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()

    def load_vip_from_file_object(self):
        csvfile = io.StringIO(self.vip_monthly_data)
        reader = VipMonthlyReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()

    def test_employee_file_object(self):
        self.load_employees_from_file_object()
        self.assertEqual(Employee.objects.all().count(), 8)
        self.assertEqual(Employee.objects.filter(termination_date__isnull=True).count(), 7)

    def test_openingbalances_file_object(self):
        self.load_employees_from_file_object()
        csvfile = io.StringIO(self.opening_balances)
        reader = OpeningBalancesReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()

    def test_import_hrm_monthly_file_object(self):
        """Asserts HrmMonthlyReader sums balance if more than one record per employee."""
        self.load_employees_from_file_object()
        csvfile = io.StringIO(self.hrm_monthly_data)
        reader = HrmMonthlyReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()
        self.assertEqual(HrmMonthly.objects.all().count(), 5)
        expected_values = [('573', Decimal('5.00')),
                           ('153', Decimal('18.00')),
                           ('644', Decimal('4.00')),
                           ('784', Decimal('6.00')),
                           ('785', Decimal('6.00'))]
        for employee_number, balance in expected_values:
            employee = Employee.objects.get(employee_number=employee_number)
            self.assertEqual(HrmMonthly.objects.filter(employee=employee).count(), 1)
            saved_balance = HrmMonthly.objects.get(employee=employee).balance
            self.assertEqual(saved_balance, balance, '{} {}!={}'.format(employee, saved_balance, balance))

    def test_import_vip_monthly_file_object(self):
        """Asserts VipMonthlyReader sums balance if more than one record per employee."""
        self.load_employees_from_file_object()
        for n in [0, 1]:
            csvfile = io.StringIO(self.vip_monthly_data)
            reader = VipMonthlyReader(filename=None, month=7 + n, year=2015, file_object=csvfile)
            reader.load()
            self.assertEqual(VipMonthly.objects.all().count(), 4 * (n + 1))
            expected_values = [('573', Decimal('13.30')),
                               ('153', Decimal('3.17')),
                               ('906', Decimal('4.17')),
                               ('784', Decimal('13.67'))]
            for employee_number, balance in expected_values:
                employee = Employee.objects.get(employee_number=employee_number)
                leave_period_start = reader.period_start
                leave_period_end = reader.period_end
                self.assertEqual(VipMonthly.objects.filter(
                    employee=employee,
                    leave_period_start=leave_period_start,
                    leave_period_end=leave_period_end,
                ).count(), 1)
                saved_balance = VipMonthly.objects.get(
                    employee=employee,
                    leave_period_start=leave_period_start,
                    leave_period_end=leave_period_end,
                ).balance
                self.assertEqual(saved_balance, balance, '{} {}!={}'.format(employee, saved_balance, balance))

    def test_import_hrm_monthly(self):
        self.assertEqual(Employee.objects.all().count(), 375)
        csvfile = '~/source/hrm/data/hrm201508.csv'
        hrm_reader = HrmMonthlyReader(csvfile, 8, 2015)
        hrm_reader.load()
        self.assertEqual(HrmMonthly.objects.all().count(), 85)
        self.assertEqual(HrmMonthly.objects.filter(
            leave_period_start=date(2015, 8, 1),
            leave_period_end=date(2015, 8, 31),
        ).count(), 85)

    def test_import_vip_monthly(self):
        csvfile = '~/source/hrm/data/vip201508.csv'
        reader = VipMonthlyReader(csvfile, 8, 2015)
        reader.load()
        self.assertEqual(VipMonthly.objects.all().count(), 292)

    def test_match_employee(self):
        csvfile = '~/source/hrm/data/hrm_usage201508.csv'
        hrm_reader = HrmUsageReportReader(csvfile, 8, 2015)
        hrm_reader.load()
        csvfile = '~/source/hrm/data/vip201508.csv'
        reader = VipMonthlyReader(csvfile, 8, 2015)
        reader.load()
        for hrm in Hrm.objects.all():
            try:
                VipMonthly.objects.get(employee=hrm.employee)
            except VipMonthly.DoesNotExist:
                print('During test, not in VipMonthly but in HRM Usage. Got {}.'.format(hrm.employee))

    def test_summary_balance_algorithm(self):
        opening = 12
        hrm = (5, 0, 2)
        vip = (7, 7, 5)
        for i, balance in enumerate(vip):
            self.assertEqual(opening - balance, hrm[i])
            opening = balance

    def test_summary_balance(self):
        self.load_employees_from_file_object()
        csvfile = io.StringIO(self.hrm_monthly_data)
        reader = HrmMonthlyReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()
        csvfile = io.StringIO(self.vip_monthly_data)
        reader = VipMonthlyReader(filename=None, month=8, year=2015, file_object=csvfile)
        reader.load()

    def test_balances(self):
        self.load_employees_from_file_object()
        self.load_openingbalances_from_file_object()
        self.load_hrm_from_file_object()
        self.load_vip_from_file_object()

    def test_verify_employee(self):
        self.load_employees_from_file_object()
        filetext = ('Number,Name\n10,Erik\n573,Moraz\n')
        csvfile = io.StringIO(filetext)
        employee = EmployeeReader(filename=None, file_object=csvfile)
        missing = employee.verify_employees(0, 1)
        self.assertEquals(missing, {'10': 'Erik'})
