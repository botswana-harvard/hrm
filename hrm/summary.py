import calendar
import csv
import os

from collections import OrderedDict
from copy import copy
from datetime import date

from .models import Employee, VipMonthly, HrmMonthly, OpeningBalances


class Summarize():

    def __init__(self, path):
        self.summary_path = os.path.join(
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

    def monthly(self):
        data = []
        data.append(self.header_row)
        for employee in Employee.objects.all().order_by('lastname'):
            try:
                opening_balance = OpeningBalances.objects.get(employee=employee).balance
            except OpeningBalances.DoesNotExist:
                opening_balance = 0
            record = copy(self.record)
            record.update(employee_number=employee.employee_number)
            record.update(lastname=employee.lastname)
            record.update(firstname=employee.firstname)
            record.update(termination_date=employee.termination_date)
            record.update(opening=opening_balance)
            for model, prefix in [(VipMonthly, 'V'), (HrmMonthly, 'H')]:
                for instance in model.objects.filter(employee=employee).order_by('leave_period_end'):
                    record.update({
                        '{}{}'.format(prefix, instance.leave_period_end.strftime('%Y%m')): instance.balance}
                    )
            row = []
            for key in self.header:
                row.append(record.get(key))
            data.append(row)
        self.write(data)
        return data

    def write(self, data):
        with open(self.summary_path, 'a') as f:
            csvwriter = csv.writer(f)
            for row in data:
                csvwriter.writerow(row)
