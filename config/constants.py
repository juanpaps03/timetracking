from collections import OrderedDict

# # General
# starting year
START_YEAR = 2018
# suffix for general tasks of each task category.
GENERAL_CODE_SUFFIX = 'GR'


# # Special Tasks
# name for "Special" task category.
SPECIAL_CATEGORY_NAME = 'Special'
# special task code for worker absences.
ABSENCE_CODE = 'F'
# special task code for worker absences with notice.
NOTICED_ABSENCE_CODE = 'FA'
# special task code for sick workers.
SICK_CODE = 'E'
# special task code for bereavement leave.
BEREAVEMENT_LEAVE_CODE = 'LD'
# special task code for study leave.
STUDY_LEAVE_CODE = 'LE'
# special task code for suspended workers.
SUSPENDED_CODE = 'S'
# special task code for union assembly.
UNION_ASSEMBLY_CODE = 'AS'
# special task code for blood donation.
BLOOD_DONATION_CODE = 'DS'
# special task code for disabled child leave.
DISABLED_CHILD_LEAVE_CODE = 'LHD'
# special task code for marriage leave.
MARRIAGE_LEAVE_CODE = 'LM'
# special task code for paternity leave.
PATERNITY_LEAVE_CODE = 'LP'
# special task code for strikes.
STRIKE_CODE = 'P'
# special task code for general strikes.
GENERAL_STRIKE_CODE = 'PG'
# special task code for syndical leave
UNION_LEAVE_CODE = 'LS'
# special task code for early leaving
EARLY_LEAVE_CODE = 'SA'
# special code for FOCAP training
FOCAP_TRAINING_CODE = 'FOCAP'
# special code for training
TRAINING_CODE = 'CAP'
# antiquity leave
ANTIQUITY_LEAVE_CODE = 'LA'
# postobra
POST_OBRA_CODE = 'POST'


# for reports, minimum widths for some of the columns.
MIN_WORKER_CODE_WIDTH = 4
MIN_FULL_NAME_WIDTH = 15
MIN_WORKER_CATEGORY_WIDTH = 4


# this is a yearly array, first position is for start year. start and end date is included in winter period.
WINTER_PERIOD = [
    ('2018-03-11', '2018-10-15'),
    ('2019-03-10', '2019-10-14'),
    ('2020-03-08', '2020-10-19'),
    ('2021-03-14', '2021-10-18'),
    ('2022-03-13', '2022-10-17')
]


# DYNAMIC CONSTANTS DEFAULTS:
DYNAMIC_CONSTANTS = {
    'COMPANY_NAME': ('Sabyl Constructora', 'Name of the company'),
    'DAYS_ABLE_TO_EDIT': (7, 'time period in days for which the overseer can edit previous workdays'),
    'DAYS_ABLE_TO_VIEW': (36500, 'time period in days for which the overseer can view previous workdays'
                                 '(default 100 years)'),
    'MONDAY_HOURS': (9, 'hours expected for mondays'),
    'TUESDAY_HOURS': (9, 'hours expected for tuesdays'),
    'WEDNESDAY_HOURS': (9, 'hours expected for wednesdays'),
    'THURSDAY_HOURS': (9, 'hours expected for thursdays'),
    'FRIDAY_HOURS': (8, 'hours expected for fridays'),
    'SATURDAY_HOURS': (0, 'hours expected for saturdays'),
    'SUNDAY_HOURS': (0, 'hours expected for sundays'),
    'INCENTIVE_THRESHOLD': (44, 'amount of hours worked needed in a week to get incentive'),
    'INCENTIVE_PERCENT': (10.42, 'bonus percent for reaching the threshold of hours needed in a week'),
    'WINTER_TIME_THRESHOLD': (4.5, 'additional half hour threshold for winter time.'),
    'SUMMER_TIME_THRESHOLD': (5, 'additional half hour threshold for summer time.'),

}

DYNAMIC_CONSTANT_FIELDSETS = OrderedDict([
    ('General Options', ('COMPANY_NAME', 'DAYS_ABLE_TO_EDIT', 'DAYS_ABLE_TO_VIEW')),
    ('Expected hours', ('MONDAY_HOURS', 'TUESDAY_HOURS', 'WEDNESDAY_HOURS', 'THURSDAY_HOURS', 'FRIDAY_HOURS',
                        'SATURDAY_HOURS', 'SUNDAY_HOURS')),
    ('Bonus hours', ('INCENTIVE_THRESHOLD', 'INCENTIVE_PERCENT', 'WINTER_TIME_THRESHOLD', 'SUMMER_TIME_THRESHOLD')),
])
