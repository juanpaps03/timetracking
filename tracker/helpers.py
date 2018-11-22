from tracker.models import *
import csv
# methods to mass-add new objects.


def add_task_categories(file_name):
    try:
        csvfile = open(file_name, 'rt')
    except:
        print("File not found")
    csv_reader = csv.reader(csvfile, delimiter=",")
    categories = list()
    for row in csv_reader:
        categories.append(row)
    counter = 0
    for category_data in categories:
        category, created = TaskCategory.objects.update_or_create(name=category_data[0])
        if created:
            counter += 1
    print(counter, 'out of', len(categories), 'categories added.')


def add_worker_categories(file_name):
    try:
        csvfile = open(file_name, 'rt')
    except:
        print("File not found")
    csv_reader = csv.reader(csvfile, delimiter=",")
    categories = list()
    for row in csv_reader:
        categories.append(row)
    counter = 0
    for category_data in categories:
        category, created = WorkerCategory.objects.update_or_create(name=category_data[0])
        if created:
            counter += 1
    print(counter, 'out of', len(categories), 'categories added.')


def add_workers(file_name):
    try:
        csvfile = open(file_name, 'rt')
    except:
        print("File not found")
    csv_reader = csv.reader(csvfile, delimiter=",")
    workers = list()
    for row in csv_reader:
        workers.append(row)
    counter = 0
    for worker_data in workers:
        worker, created = Worker.objects.update_or_create(code=worker_data[0],
                                                          defaults={
                                                                    "first_name": worker_data[1],
                                                                    "last_name": worker_data[2],
                                                                    "category_id": worker_data[3]})
        if created:
            counter += 1
    print(counter, 'out of', len(workers), 'workers added.')


def add_tasks(file_name):
    try:
        csvfile = open(file_name, 'rt')
    except:
        print("File not found")
    csv_reader = csv.reader(csvfile, delimiter=",")
    tasks = list()
    for row in csv_reader:
        tasks.append(row)
    counter = 0
    for task_data in tasks:
        task, created = Task.objects.update_or_create(code=task_data[0],
                                                      defaults={
                                                             "name": task_data[1],
                                                             "description": task_data[2],
                                                             "category_id": task_data[3],
                                                             "requires_comment": task_data[4] == 'TRUE',
                                                             "is_boolean": task_data[5] == 'TRUE',
                                                             "whole_day": task_data[6] == 'TRUE',
                                                             "in_monthly_report": task_data[7] == 'TRUE'})
        if created:
            counter += 1
    print(counter, 'out of', len(tasks), 'tasks added.')
