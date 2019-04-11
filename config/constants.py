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
# rain
RAIN_CODE = 'LL'


# for reports, minimum widths for some of the columns.
MIN_WORKER_CODE_WIDTH = 6.5
MIN_FULL_NAME_WIDTH = 20
MIN_WORKER_CATEGORY_WIDTH = 4
MIN_TITLE_ROW_HEIGHT = 20


# winter period goes from second sunday of march until third monday of october.
# this is a yearly array, first position is for start year. start and end date is included in winter period.
WINTER_PERIOD = [
    ('2018-03-11', '2018-10-15'),
    ('2019-03-10', '2019-10-14'),
    ('2020-03-08', '2020-10-19'),
    ('2021-03-14', '2021-10-18'),
    ('2022-03-13', '2022-10-17'),
    ('2023-03-12)', '2023-10-26'),
    ('2024-03-10)', '2024-10-21'),
    ('2025-03-09)', '2025-10-20'),
    ('2026-03-08)', '2026-10-19'),
    ('2027-03-14)', '2027-10-18'),
    ('2028-03-12)', '2028-10-16'),
    ('2029-03-11)', '2029-10-15'),
    ('2030-03-10)', '2030-10-21'),
    ('2031-03-09)', '2031-10-20'),
    ('2032-03-14)', '2032-10-18'),
    ('2033-03-13)', '2033-10-17'),
    ('2034-03-12)', '2034-10-16'),
    ('2035-03-11)', '2035-10-15'),
    ('2036-03-09)', '2036-10-20'),
    ('2037-03-08)', '2037-10-19'),
    ('2038-03-14)', '2038-10-18'),
    ('2039-03-13)', '2039-10-17'),
    ('2040-03-11)', '2040-10-15')
]


# DYNAMIC CONSTANTS DEFAULTS:
DYNAMIC_CONSTANTS = {
    'COMPANY_NAME': ('Sabyl Constructora', 'Nombre de la empresa'),
    'DAYS_ABLE_TO_EDIT': (7, 'Cantidad de días pasados que un capataz puede editar.'),
    'DAYS_ABLE_TO_VIEW': (36500, 'Cantidad de días pasados que un capataz puede ver (por defecto 100 años).'),
    'MONDAY_HOURS': (9, 'Horas de trabajo esperadas los días lunes.'),
    'TUESDAY_HOURS': (9, 'Horas de trabajo esperadas los días martes.'),
    'WEDNESDAY_HOURS': (9, 'Horas de trabajo esperadas los días miércoles.'),
    'THURSDAY_HOURS': (9, 'Horas de trabajo esperadas los días jueves.'),
    'FRIDAY_HOURS': (8, 'Horas de trabajo esperadas los días viernes.'),
    'SATURDAY_HOURS': (0, 'Horas de trabajo esperadas los días sábado.'),
    'SUNDAY_HOURS': (0, 'Horas de trabajo esperadas los días domingo.'),
    'INCENTIVE_THRESHOLD': (44, 'Cantidad de horas de trabajo semanales necesarias para cobrar incentivo.'),
    'INCENTIVE_PERCENT': (10.42, 'Porcentaje de incentivo sobre las horas semanales trabajadas.'),
    'WINTER_TIME_THRESHOLD': (4.5, 'Cantidad de horas de trabajo para cobrar media hora adicional en invierno.'),
    'SUMMER_TIME_THRESHOLD': (5, 'Cantidad de horas de trabajo para cobrar media hora adicional en verano.'),

}

DYNAMIC_CONSTANT_FIELDSETS = OrderedDict([
    ('Opciones Generales', ('COMPANY_NAME', 'DAYS_ABLE_TO_EDIT', 'DAYS_ABLE_TO_VIEW')),
    ('Horas esperadas', ('MONDAY_HOURS', 'TUESDAY_HOURS', 'WEDNESDAY_HOURS', 'THURSDAY_HOURS', 'FRIDAY_HOURS',
                         'SATURDAY_HOURS', 'SUNDAY_HOURS')),
    ('Adicionales', ('INCENTIVE_THRESHOLD', 'INCENTIVE_PERCENT', 'WINTER_TIME_THRESHOLD', 'SUMMER_TIME_THRESHOLD')),
])
