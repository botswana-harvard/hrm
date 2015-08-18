import csv
import os

from datetime import datetime
from decimal import Decimal

from .models import Hrm, Vip


def export():
    total = 0
    filename = 'export_{}.csv'.format(datetime.today().strftime('%Y%m%d'))
    path = os.path.join(os.path.expanduser('~/'), filename)
    with open(path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'employee_number', 'lastname', 'firstname', 'localtion', 'subunit', 'period',
            'entitlements', 'pending_approval', 'scheduled', 'taken', 'available_balance',
            'total_overdrawn', 'hrm', 'vip', 'diff', 'gr_in_hrm', 'gr_in_vip', 'excessive'])
        for vip in Vip.objects.all():
            try:
                hrm = Hrm.objects.get(employee=vip.employee)
                writer.writerow([
                    hrm.employee.employee_number,
                    hrm.employee.lastname,
                    hrm.employee.firstname,
                    hrm.employee.location,
                    hrm.employee.subunit,
                    '{} - {}'.format(
                        hrm.leave_period_start.strftime('%Y-%m-%d'),
                        hrm.leave_period_end.strftime('%Y-%m-%d')
                    ),
                    hrm.entitlements,
                    hrm.pending_approval,
                    hrm.scheduled,
                    hrm.taken,
                    hrm.available_balance,
                    hrm.total_overdrawn,
                    hrm.hrm_balance,
                    hrm.vip_balance,
                    hrm.hrm_balance - vip.balance,
                    abs(hrm.hrm_balance - vip.balance) if (hrm.hrm_balance - vip.balance) > 0 else None,
                    abs(hrm.hrm_balance - vip.balance) if (hrm.hrm_balance - vip.balance) < 0 else None,
                    abs(hrm.hrm_balance - vip.balance) if abs(hrm.hrm_balance - vip.balance) >= 4.16 else None,
                ])
                total += hrm.hrm_balance - (hrm.vip_balance or Decimal(0.00))
            except Hrm.DoesNotExist:
                pass
    print('total={}'.format(total))
    print('Exported to {}'.format(path))
