# # General
# starting year of deployment (for year selection in reports)
START_YEAR = 2018
# company name.
COMPANY_NAME = 'Sabyl Constructora'
# time period for which the overseer can edit previous workdays.
DAYS_ABLE_TO_EDIT = 7
# time period for which the overseer can view previous workdays.
DAYS_ABLE_TO_VIEW = 3650
# amount of hours workers are expected to work each day of the week (in monday to sunday format)
EXPECTED_HOURS = [9, 9, 9, 9, 8, 0, 0]
# suffix for general tasks in each category.
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


# incentive hours threshold for computation
INCENTIVE_THRESHOLD = 44
# incentive hours percentage
INCENTIVE_PERCENT = 10.42

# additional half hours
WINTER_TIME_THRESHOLD = 4.5
SUMMER_TIME_THRESHOLD = 5
# this is a yearly array, first position is for start year. start and end date is included in winter period.
WINTER_PERIOD = [
    ('2018-03-11', '2018-10-15'),
    ('2019-03-10', '2019-10-14'),
    ('2020-03-08', '2020-10-19'),
    ('2021-03-14', '2021-10-18'),
    ('2022-03-13', '2022-10-17')
]

