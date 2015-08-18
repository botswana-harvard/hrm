import csv
import os

from datetime import date, timedelta
from decimal import Decimal
from dateutil.parser import parse

from .models import Hrm, Vip, Employee
from django.db.utils import IntegrityError
from django.db import transaction


class BaseHrm(object):

    encoding = 'utf-8'

    def __init__(self, filename, delimiter=None):
        self.filename = os.path.expanduser(filename)
        self.delimiter = ','

    def names(self, values):
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


class HrmReader(BaseHrm):

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
                print(firstname, middlename, lastname, strippedname)
        return employee

    def load(self):
        Hrm.objects.all().delete()
        with open(self.filename, encoding=self.encoding, newline='') as f:
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
                        leave_period_start=parse(values[1].split('-')[0]),
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
        return Hrm.objects.all().count()

    def hrm_balance(self, hrm):
        return hrm.entitlements - (hrm.pending_approval + hrm.scheduled or + hrm.taken)


class EmployeeReader(BaseHrm):

    def load(self):
        Employee.objects.all().delete()
        with open(self.filename, encoding=self.encoding, newline='') as f:
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
                            strippedname=strippedname,
                        )
                    except IntegrityError as e:
                        print(str(e), firstname, middlename, lastname, strippedname)
        return Employee.objects.all().count()


class VipReader(object):
    encoding = 'utf-8'

    def __init__(self, filename, month, year, delimiter=None):
        self.filename = os.path.expanduser(filename)
        self.delimiter = ','
        self.period_start = date(year, month, 1)
        self.period_end = date(year, month + 1, 1) - timedelta(days=1)

    def load(self):
        Vip.objects.all().delete()
        with open(self.filename, encoding=self.encoding, newline='') as f:
            reader = csv.reader(f, delimiter=self.delimiter)
            for values in reader:
                lastname = values[1].split(' ')
                lastname = lastname[len(lastname) - 1].replace(' ', '')
                try:
                    employee = Employee.objects.get(employee_number=values[0])
                    vip = Vip.objects.create(
                        employee=employee,
                        employee_number=values[0],
                        fullname=values[1],
                        leave_period_start=self.period_start,
                        leave_period_end=self.period_end,
                        balance=values[2]
                    )
                    try:
                        hrm = Hrm.objects.get(employee=employee)
                        hrm.vip_balance = vip.balance
                        hrm.save()
                    except Hrm.DoesNotExist:
                        pass
                except Employee.DoesNotExist:
                    print(values)
        return Vip.objects.all().count()
