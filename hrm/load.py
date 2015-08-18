from .readers import EmployeeReader, HrmReader, VipReader


def load_employee():
    csvfile = '~/source/hrm/hrm/data/employee.csv'
    reader = EmployeeReader(csvfile)
    return reader.load()


def load_hrm():
    csvfile = '~/source/hrm/hrm/data/hrm.csv'
    hrm_reader = HrmReader(csvfile)
    return hrm_reader.load()


def load_vip():
    csvfile = '~/source/hrm/hrm/data/vip.csv'
    reader = VipReader(csvfile, 8, 2015)
    return reader.load()


def load_all():
    e = load_employee()
    h = load_hrm()
    v = load_vip()
    print('Employees: {}, Hrm:{}, Vip:{}'.format(e, h, v))
