def serialize_task(task, with_logs=False):
    if with_logs:
        return {
            'id': task.id,
            'code': task.code,
            'name': task.name,
            'category': task.category.name,
            'description': task.description,
            'requires_comment': task.requires_comment,
            'is_boolean': task.is_boolean,
            'logs': [{'worker': {'code': log.worker.code}, 'amount': float(log.amount)} for log in task.logs],
        }
    else:
        return {
            'id': task.id,
            'code': task.code,
            'name': task.name,
            'category': task.category.name,
            'description': task.description,
            'requires_comment': task.requires_comment,
            'is_boolean': task.is_boolean
        }


def serialize_tasks_with_logs(tasks):
    return [serialize_task(task, with_logs=True) for task in tasks]


def serialize_log(log, with_worker=False, with_task=False):
    if with_worker and with_task:
        return {
            'task': serialize_task(log.task),
            'worker': {'code': log.worker.code, 'first_name': log.worker.first_name, 'last_name': log.worker.last_name},
            'amount': float(log.amount),
            'comment': log.comment
        }
    elif with_worker:
        return {
            'worker': {'code': log.worker.code, 'first_name': log.worker.first_name, 'last_name': log.worker.last_name},
            'amount': float(log.amount),
            'comment': log.comment
        }
    elif with_task:
        return {
            'task': serialize_task(log.task),
            'amount': float(log.amount),
            'comment': log.comment
        }
    else:
        return {
            'amount': float(log.amount),
            'comment': log.comment
        }


def serialize_logs(logs, with_workers, with_tasks):
    return [serialize_log(log, with_workers, with_tasks) for log in logs]


def serialize_worker_with_logs(worker):
    return {
        'code': worker.code,
        'first_name': worker.first_name,
        'last_name': worker.last_name,
        'category': worker.category.name,
        'logs': serialize_logs(worker.logs, with_tasks=True, with_workers=False),
        'passes_controls': worker.passes_controls,
        'hours_percent': worker.hours_percent
    }


def serialize_workers_with_logs(workers):
    return [serialize_worker_with_logs(worker) for worker in workers]
