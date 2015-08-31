from datetime import date
from dateutil.relativedelta import relativedelta
from django.db.models import Q

from .models import Employee
from .load import load_employee
from hrm.load import load_vip_monthly
from hrm.models import VipMonthly


class Employees(object):

    def __init__(self, start_date, end_date, load=None):
        if load:
            Employee.objects.all().delete()
            load_employee()
            load_vip_monthly()
        self.total = Employee.objects.all().count()
        self.joined = []
        self.terminated = []
        start_date = start_date or date(1900, 1, 1)
        count = self.joined_in_period(start_date, end_date).count()
        self.joined.append((end_date + relativedelta(day=1), count))
        count = self.terminated_in_period(start_date, end_date).count()
        self.terminated.append((end_date + relativedelta(day=1), count))
        for _ in range(0, 9):
            end_date = (end_date + relativedelta(months=1)) + relativedelta(day=31)
            start_date = end_date + relativedelta(day=1)
            count = self.joined_in_period(start_date, end_date).count()
            self.joined.append((start_date, count))
            count = self.terminated_in_period(start_date, end_date).count()
            self.terminated.append((start_date, count))

    def joined_in_period(self, start_date, end_date):
        return Employee.objects.filter(
            joined__range=(start_date, end_date),
        )

    def terminated_in_period(self, start_date, end_date):
        return Employee.objects.filter(
            termination_date__range=(start_date, end_date),
        )

    def active_employees(self, end_date):
        """Returns a queryset of active employees as of a month end."""
        return self.joined_in_period(date(1900, 1, 1), end_date).filter(
            (Q(termination_date__isnull=True) |
             Q(termination_date__gte=end_date)),
        )

    def active_employees_in_vip(self, end_date):
        return VipMonthly.objects.filter(
            transaction_date__gte=end_date + relativedelta(day=1),
            transaction_date__lte=end_date)
