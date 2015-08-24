import csv
import os

from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse

from django.db.utils import IntegrityError
from django.db import transaction

from .models import Hrm, VipMonthly, HrmMonthly, Employee
from hrm.models import OpeningBalances


class BaseReader(object):

    encoding = 'utf-8'
    model = None

    def __init__(self, filename, delimiter=None, file_object=None):
        self.file_object = file_object
        try:
            self.filename = os.path.expanduser(filename)
        except AttributeError:
            self.filename = None
        self.delimiter = ','

    def load(self):
        self.pre_load()
        if self.file_object:
            self.load_process(self.file_object)
        else:
            with open(self.filename, encoding=self.encoding, newline='') as f:
                self.load_process(f)
        return self.post_load()

    def pre_load(self):
        self.model.objects.all().delete()

    def load_process(self, file_object=None):
        """Override to update the model from the file-like object."""
        pass

    def post_load(self):
        return self.model.objects.all().count()

    def employee(self, firstname, middlename, lastname, strippedname):
        try:
            employee = Employee.objects.get(
                lastname=lastname, firstname=firstname, middlename=middlename)
        except Employee.DoesNotExist:
            try:
                employee = Employee.objects.get(
                    strippedname=strippedname)
            except Employee.DoesNotExist:
                employee = None
                print('Employee in {} not found. Got {} {} {}.'.format(
                    self.model._meta.verbose_name, firstname, middlename, lastname))
        return employee

    def names(self, values):
        values = [v for v in values if v]
        values = [v for v in values if (v != '(Past' and v != 'Employee)')]
        if len(values) > 3:
            values.remove(values[1])
        firstname = values[0].strip()
        if len(values) == 3:
            middlename = values[1].strip()
            lastname = values[2].strip()
        else:
            middlename = None
            lastname = values[1].strip()
        strippedname = '{}{}{}'.format(firstname, middlename or '', lastname).strip().replace(' ', '')
        return firstname, middlename, lastname, strippedname


class HrmUsageReportReader(BaseReader):
    """Loads 'Leave Entitlement and Usage Report' csv export file.

        Calculates a leave days balance, hrm_balance, as of the time of the report.
        """
    model = Hrm

    def __init__(self, filename, month, year, delimiter=None):
        self.period_start = date(year, month, 1)
        self.period_end = (self.period_start + relativedelta(months=+1)) - timedelta(days=1)
        super().__init__(filename, delimiter)

    def pre_load(self):
        self.model.objects.filter(
            leave_period_start=self.period_start,
            leave_period_end=self.period_end,
        ).delete()

    def hrm_balance(self, hrm):
        return hrm.entitlements - (hrm.pending_approval + hrm.scheduled + hrm.taken)

    def load_process(self, f):
        reader = csv.reader(f, delimiter=self.delimiter)
        header = next(reader)
        header = [h.lower() for h in header]
        for values in reader:
            firstname, middlename, lastname, strippedname = self.names(values[0].split(' '))
            employee = self.employee(firstname, middlename, lastname, strippedname)
            if employee:
                hrm = Hrm(
                    employee=employee,
                    fullname=values[0],
                    leave_period_start=parse(values[1].split('-')[1]),
                    leave_period_end=parse(values[1].split('-')[0]),
                    entitlements=Decimal(values[2]),
                    pending_approval=Decimal(values[3]),
                    scheduled=Decimal(values[4]),
                    taken=Decimal(values[5]),
                    available_balance=Decimal(values[6]),
                    total_overdrawn=Decimal(values[7]),
                )
                hrm.hrm_balance = self.hrm_balance(hrm)
                hrm.save()


class EmployeeReader(BaseReader):

    model = Employee

    def load_process(self, f):
        reader = csv.reader(f, delimiter=self.delimiter)
        header = next(reader)
        header = [h.lower() for h in header]
        for values in reader:
            with transaction.atomic():
                try:
                    firstname, middlename, lastname, strippedname = self.names(
                        [values[2]] + values[1].replace('  ', ' ').split(' ')
                    )
                    Employee.objects.create(
                        employee_number=str(int(values[0])),
                        lastname=lastname,
                        firstname=firstname,
                        middlename=middlename,
                        subunit=str(values[6]),
                        location=str(values[7]),
                        job_title=str(values[3]),
                        employment_status=str(values[4]),
                        joined=parse(values[5]),
                        termination_date=parse(values[8]) if values[8] else None,
                        strippedname=strippedname,
                    )
                except IntegrityError as e:
                    print('Duplicate employee {} {} {}. Got {}.'.format(firstname, middlename, lastname, str(e)))

    def verify_employees(self, number, name):
        if self.file_object:
            missing = self.verify_file(self.file_object, number, name)
        else:
            with open(self.filename, encoding=self.encoding, newline='') as f:
                missing = self.verify_file(f, number, name)
        return missing

    def verify_file(self, f, number, name):
        """Returns a dictionary of employees list in the file but not in Employees."""
        missing = {}
        soft_match = {}
        reader = csv.reader(f, delimiter=self.delimiter)
        next(reader)
        for values in reader:
            lastname = [v for v in values[name].split(' ') if v][-1:][0]
            employee_number = int(values[number])
            try:
                Employee.objects.get(employee_number=employee_number, lastname=lastname)
            except Employee.DoesNotExist:
                try:
                    employee = Employee.objects.get(lastname__icontains=lastname)
                    option = Employee.objects.get(employee_number=employee_number)
                    soft_match.update(
                        {values[number]: [
                            values[name],
                            '{} {} {}'.format(employee.employee_number, employee.lastname, employee.firstname),
                            '{} {} {}'.format(option.employee_number, option.lastname, option.firstname)]}
                    )
                    print('Soft match:{} {}'.format(values[number], soft_match.get(values[number])))
                except Employee.DoesNotExist:
                    missing.update({values[number]: values[name]})
                    print('Employee not found. Got {}: {}'.format(employee_number, lastname))
        return missing

    def add_missing_employee(self):
        pass


class BaseMonthlyReader(BaseReader):
    """Loads a VIP export file of number, name and balance as of YYYY-MM-DD."""

    encoding = 'utf-8'
    model = VipMonthly
    EMPLOYEE_NUMBER = 0
    EMPLOYEE_NAME = 1
    BALANCE = 2

    def __init__(self, filename, month, year, delimiter=None, file_object=None):
        self.delimiter = ','
        self.period_start = date(year, month, 1)
        self.period_end = (self.period_start + relativedelta(months=+1)) - timedelta(days=1)
        super().__init__(filename, delimiter, file_object)

    def pre_load(self):
        self.model.objects.filter(
            leave_period_start=self.period_start,
            leave_period_end=self.period_end,
        ).delete()

    def load_process(self, f):
        header = None
        reader = csv.reader(f, delimiter=self.delimiter)
        for values in reader:
            if not header:
                header = values
            else:
                obj, employee = self.update_model(values)
                if obj:
                    self.update_hrm_balance(employee, obj)

    def post_load(self):
        return self.model.objects.filter(
            leave_period_start=self.period_start,
            leave_period_end=self.period_end,
        ).count()

    def employee(self, values):
        try:
            employee = Employee.objects.get(employee_number=int(values[self.EMPLOYEE_NUMBER]))
        except Employee.DoesNotExist:
            employee = None
            print("Employee listed in {} not found. Got {} {}".format(
                self.model._meta.verbose_name, int(values[self.EMPLOYEE_NUMBER]), values[self.EMPLOYEE_NAME]))
        return employee

    def update_model(self, values):
        obj = None
        employee = self.employee(values)
        if employee:
            try:
                obj = self.model.objects.get(
                    employee=employee,
                    leave_period_start=self.period_start,
                    leave_period_end=self.period_end
                )
                obj.balance = obj.balance + Decimal(values[self.BALANCE])
                obj.save()
            except self.model.DoesNotExist:
                obj = self.model.objects.create(
                    employee=employee,
                    employee_number=employee.employee_number,
                    fullname=values[self.EMPLOYEE_NAME],
                    leave_period_start=self.period_start,
                    leave_period_end=self.period_end,
                    balance=Decimal(values[self.BALANCE]),
                )
        return obj, employee

    def update_hrm_balance(self, employee, obj):
        try:
            hrm = Hrm.objects.get(employee=employee)
            hrm.vip_balance += obj.balance
            hrm.save()
        except Hrm.DoesNotExist:
            if not employee.termination_date:
                pass
                # print('Cannot update balance. Active Employee not found in {}. {}'.format(Hrm._meta.verbose_name, employee))


class VipMonthlyReader(BaseMonthlyReader):

    def __init__(self, filename, month, year, delimiter=None, file_object=None):
        self.opening_balances = {}
        for obj in OpeningBalances.objects.all():
            self.opening_balances[str(obj.employee_number)] = Decimal(obj.balance or '0.00')
        super().__init__(filename, month, year, delimiter, file_object)

    def update_model(self, values):
        """Updates the model.
        VIP balance includes accrued (2.08)."""
        employee = self.employee(values)
        if employee:
            try:
                balance = values[self.BALANCE]
                values[self.BALANCE] = (
                    self.opening_balances.get(str(employee.employee_number)) - Decimal(values[self.BALANCE] or '0.00')
                )
                values[self.BALANCE] = values[self.BALANCE] - Decimal('2.08')
                self.opening_balances[str(employee.employee_number)] = balance
            except TypeError:
                print(
                    'No opening balance for {}: {}. Got {}'.format(
                        employee.employee_number,
                        employee.lastname,
                        self.opening_balances.get(str(employee.employee_number)))
                )
        return super().update_model(values)


class HrmMonthlyReader(BaseMonthlyReader):
    """Loads a HRM 'Leave List' export file of number, name and balance as of YYYY-MM-DD."""

    model = HrmMonthly
    Date = 0
    EMPLOYEE_NAME = 1
    LEAVETYPE = 2
    BALANCE = 3
    Status = 4
    Comments = 5

    def load_process(self, f):
        header = None
        reader = csv.reader(f, delimiter=self.delimiter)
        for values in reader:
            if not header:
                header = values
            else:
                if values[self.LEAVETYPE] == 'Annual Leave':
                    self.update_model(values)

    def employee(self, values):
        firstname, middlename, lastname, strippedname = self.names(values[self.EMPLOYEE_NAME].split(' '))
        try:
            employee = Employee.objects.get(
                lastname=lastname, firstname=firstname)
        except Employee.DoesNotExist:
            try:
                employee = Employee.objects.get(
                    strippedname=strippedname)
            except Employee.DoesNotExist:
                employee = None
                print("Employee in {} not found. Got {} {} {}".format(
                    self.model._meta.verbose_name, firstname, middlename, lastname))
        return employee


class OpeningBalancesReader(BaseMonthlyReader):

    model = OpeningBalances
    EMPLOYEE_NUMBER = 0
    LASTNAME = 1
    FIRSTNAME = 2
    JOINED = 3
    BALANCE = 4

    def update_model(self, values):
        """Confirms join date with employee"""
        obj, employee = super().update_model(values)
        if parse(values[self.JOINED], dayfirst=True).date() != employee.joined:
            print(
                'Non-matched joined date from open balance. Expected {}. Got {}.'.format(
                    parse(values[self.JOINED], dayfirst=True).date(),
                    employee.joined)
            )
        return obj, employee

    def employee(self, values):
        try:
            employee = Employee.objects.get(employee_number=int(values[self.EMPLOYEE_NUMBER]))
        except Employee.DoesNotExist:
            employee = Employee.objects.create(
                employee_number=int(values[self.EMPLOYEE_NUMBER]),
                lastname=values[self.LASTNAME],
                firstname=values[self.FIRSTNAME],
                joined=parse(values[self.JOINED], dayfirst=True).date(),
                manually_added=True,
            )
        return employee
