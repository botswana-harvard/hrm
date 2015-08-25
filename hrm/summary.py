import calendar
import csv
import os

from datetime import datetime
from decimal import Decimal
from collections import OrderedDict
from copy import copy
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import Employee, VipMonthly, HrmMonthly, OpeningBalances


class Summarize:

    def __init__(self, employee, reference_date, carry_forward=None, write_path=None):
        self.employee = employee
        self.write_path = write_path
        self.reference_date = reference_date + relativedelta(day=31)
        self.opening_balance = OpeningBalances.objects.get(employee=self.employee)
        self.carry_forward = carry_forward or 0

    @property
    def balance_from_opening(self):
        rdelta = relativedelta(self.opening_balance.balance_date, self.reference_date)
        accrued = Decimal(str(abs(2.08 * rdelta.months)))
        return (
            self.opening_balance.balance + accrued -
            self.monthly_taken(self.opening_balance.balance_date, self.reference_date)
        )

    @property
    def balance_for_leave_period(self):
        leave_period_start = datetime(self.reference_date.year, self.employee.joined.month, 1)
        rdelta = relativedelta(leave_period_start, self.reference_date)
        accrued = Decimal(str(abs(2.08 * rdelta.months)))
        return self.carry_forward + accrued - self.monthly_taken(leave_period_start, self.reference_date)

    def monthly_taken(self, start_date, end_date):
        taken = Decimal('0.00')
        for hrm_monthly in HrmMonthly.objects.filter(
                employee=self.employee,
                leave_period_start__gte=start_date,
                leave_period_end__lte=end_date):
            taken += hrm_monthly.balance or Decimal('0.00')
        return taken

    def write_summary(self, path):
        self.path = os.path.join(
            os.path.expanduser(path), 'summary_{}.csv'.format(date(2014, 12, 31).strftime('%Y%m%d')))
        try:
            os.remove(self.summary_path)
        except FileNotFoundError:
            pass
        self.header_row = [
            'employee_number',
            'lastname',
            'firstname',
            'termination_date',
            'opening',
            'H{}'.format(date(2014, 12, 31).strftime('%Y%m')),
            'V{}'.format(date(2014, 12, 31).strftime('%Y%m')),
        ]
        for m in range(1, 9):
            self.header_row.append('H{}'.format(date(2015, m, calendar.monthrange(2015, m)[1]).strftime('%Y%m')))
            self.header_row.append('V{}'.format(date(2015, m, calendar.monthrange(2015, m)[1]).strftime('%Y%m')))
        self.header_row.append('total')
        self.record = OrderedDict({
            'employee_number': None,
            'lastname': None,
            'firstname': None,
            'termination_date': None,
            'opening': 0,
            'H{}'.format(date(2014, 12, 31).strftime('%Y%m')): 0,
            'V{}'.format(date(2014, 12, 31).strftime('%Y%m')): 0,
        })
        for m in range(1, 9):
            self.record[date(2015, m, calendar.monthrange(2015, m)[1]).strftime('%Y%m')] = 0
        self.record['total'] = 0

    def write(self, data):
        with open(self.summary_path, 'a') as f:
            csvwriter = csv.writer(f)
            for row in data:
                csvwriter.writerow(row)
