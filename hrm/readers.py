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
from django.core.exceptions import MultipleObjectsReturned


class BaseReader(object):

    encoding = 'latin-1'
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

    model = VipMonthly
    DATE = None
    EMPLOYEE_NUMBER = 0
    EMPLOYEE_NAME = 1
    BALANCE = 2

    def __init__(self, filename, delimiter=None, file_object=None):
        self.delimiter = ','
        super().__init__(filename, delimiter, file_object)

    def pre_load(self):
        pass

    def load_process(self, f):
        header = None
        reader = csv.reader(f, delimiter=self.delimiter)
        for values in reader:
            # print(values)
            if not header:
                header = values
            else:
                obj, employee = self.update_model(values)
                if obj:
                    self.update_hrm_balance(employee, obj)

    def post_load(self):
        pass

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
                transaction_date = parse(values[self.DATE], dayfirst=True)
            except (TypeError, IndexError):
                transaction_date = self.period_end
            try:
                obj = self.model.objects.get(
                    employee=employee,
                    leave_period_start=transaction_date + relativedelta(day=1),
                    leave_period_end=transaction_date + relativedelta(day=31),
                    transaction_date=transaction_date,
                )
                obj.balance += Decimal(values[self.BALANCE])
                obj.save()
            except self.model.DoesNotExist:
                obj = self.model.objects.create(
                    employee=employee,
                    employee_number=employee.employee_number,
                    transaction_date=transaction_date,
                    fullname=values[self.EMPLOYEE_NAME],
                    leave_period_start=transaction_date + relativedelta(day=1),
                    leave_period_end=transaction_date + relativedelta(day=31),
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


class VipMonthlyReader(BaseMonthlyReader):

    def __init__(self, filename, month, year, delimiter=None, file_object=None):
        self.period_start = date(year, month, 1)
        self.period_end = (self.period_start + relativedelta(months=+1)) - timedelta(days=1)
        super().__init__(filename, delimiter, file_object)


class HrmMonthlyReader(BaseMonthlyReader):
    """Loads a HRM 'Leave List' export file of number, name and balance as of YYYY-MM-DD."""

    model = HrmMonthly
    DATE = 0
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

    def __init__(self, filename, balance_date, delimiter=None, file_object=None):
        self.balance_date = balance_date
        super(BaseMonthlyReader, self).__init__(filename, delimiter, file_object=file_object)

    def update_model(self, values):
        """Confirms join date with employee"""
        obj = None
        employee = self.employee(values)
        if employee:
            obj = self.model.objects.create(
                employee=employee,
                balance=Decimal(values[self.BALANCE]),
                balance_date=self.balance_date
            )
        if parse(values[self.JOINED], dayfirst=True).date() != employee.joined:
            print(
                'Non-matched joined date from open balance. Expected {}. Got {}.'.format(
                    parse(values[self.JOINED], dayfirst=True).date(),
                    employee.joined)
            )
        return obj, employee

    def post_load(self):
        pass

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


class EmployeesFinanceReader:
    """Loads a HRM 'Leave List' export file of number, name and balance as of YYYY-MM-DD."""

    encoding = 'latin-1'
    NAME = 1

    def __init__(self, filename):
        filename = os.path.expanduser(filename)
        header = None
        with open(filename, encoding=self.encoding, newline='') as f:
            all_values = []
            reader = csv.reader(f, delimiter=',')
            for values in reader:
                if not header:
                    header = values
                else:
                    print(values[self.NAME])
                    all_values.append(values[self.NAME])
        values = list(set(all_values))
        for value in values:
            self.employee([value])

    def employee(self, values):
        employee = None
        new_values = values[0].replace('.', ' ').split(' ')
        new_values = [v for v in new_values if v]
        lastname = new_values[0]
        try:
            first_initial = new_values[1]
            options = {'lastname': lastname, 'firstname__startswith': first_initial[0]}
        except IndexError:
            options = {'lastname': lastname}
            first_initial = [' ']
        try:
            employee = Employee.objects.get(**options)
        except MultipleObjectsReturned:
            employees = Employee.objects.filter(**options)
            print('Employee name {} is ambiguous. Got {}'.format(values[0], [employee for employee in employees]))
        except Employee.DoesNotExist:
            print("Employee not found in HRM. Got {} {} {}".format(lastname, first_initial[0], new_values))
        return employee
