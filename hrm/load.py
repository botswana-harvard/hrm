import os

from datetime import datetime

from .readers import (
    EmployeeReader, HrmUsageReportReader, VipMonthlyReader, HrmMonthlyReader, OpeningBalancesReader)
from hrm.summary import Summarize

PERIODS = [(12, 2014), (1, 2015), (2, 2015), (3, 2015), (4, 2015), (5, 2015), (6, 2015), (7, 2015), (8, 2015)]
DEFAULT_PATH = '~/source/hrm/data/'


def load_employee(path):
    path = path or DEFAULT_PATH
    csvfile = os.path.join(path, 'employee.csv')
    reader = EmployeeReader(csvfile)
    return reader.load()


def load_hrm_usage(path):
    path = path or DEFAULT_PATH
    for m, y in [(8, 2015)]:
        csvfile = os.path.join(path, 'hrm_usage{0}{1:02d}.csv'.format(y, m))
        print(csvfile)
        hrm_reader = HrmUsageReportReader(csvfile, m, y)
        hrm_reader.load()


def load_opening_balances(path):
    path = path or DEFAULT_PATH
    csvfile = os.path.join(path, 'opening201412.csv')
    print(csvfile)
    reader = OpeningBalancesReader(csvfile, datetime.today().date())
    reader.load()


def load_vip_monthly(path):
    path = path or DEFAULT_PATH
    for m, y in PERIODS:
        csvfile = os.path.join(path, 'vip{0}{1:02d}.csv'.format(y, m))
        print(csvfile)
        reader = VipMonthlyReader(csvfile, m, y)
        reader.load()


def load_hrm_monthly(path, y, m):
    csvfile = os.path.join(path, 'leave_list{0}{1:02d}.csv'.format(y, m))
    print(csvfile)
    reader = HrmMonthlyReader(csvfile)
    reader.load()


def load_all(path, y, m):
    e = load_employee(path)
    o = load_opening_balances(path)
    h = load_hrm_usage(path)
    hm = load_hrm_monthly(path, y, m)
    vm = load_vip_monthly(path)
    # summarize = Summarize(path)
    # summarize.monthly()
    # print('Employees: {}, Usage: {}Hrm:{}, Vip:{}'.format(e, h, hm, vm))
