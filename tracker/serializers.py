def serialize_task(task, with_logs=False):
    serialized_task = {
        'id': task.id,
        'code': task.code,
        'name': task.name,
        'category': task.category.name.upper(),
        'description': task.description,
        'requires_comment': task.requires_comment,
        'is_boolean': task.is_boolean
    }
    if with_logs:
        serialized_task['logs'] = [{'worker': {'code': log.worker.code}, 'amount': float(log.amount), 'comment': log.comment} for log in task.logs]
    return serialized_task


def serialize_tasks_with_logs(tasks):
    return [serialize_task(task, with_logs=True) for task in tasks]


def serialize_log(log, with_worker=False, with_task=False):
    serialized_log = {
        'amount': float(log.amount),
        'comment': log.comment
    }
    if with_task:
        serialized_log['task'] = serialize_task(log.task)
    if with_worker:
        serialized_log['worker'] = {'code': log.worker.code,
                                    'category': {'code': log.worker.category.code, 'name': log.worker.category.name},
                                    'first_name': log.worker.first_name,
                                    'last_name': log.worker.last_name}
    return serialized_log


def serialize_logs(logs, with_workers, with_tasks):
    return [serialize_log(log, with_workers, with_tasks) for log in logs]


def serialize_worker_with_logs(worker):
    return {
        'code': worker.code,
        'first_name': worker.first_name,
        'last_name': worker.last_name,
        'category': {'code': worker.category.code, 'name': worker.category.name},
        'logs': serialize_logs(worker.logs, with_workers=False, with_tasks=True),
        'passes_controls': worker.passes_controls,
        'hours_percent': worker.hours_percent,
        'passes_controls_string': worker.passes_controls_string,
        'tiene_tarea_especial_todo_el_dia': worker.tiene_tarea_especial_todo_el_dia
    }


def serialize_workers_with_logs(workers):
    return [serialize_worker_with_logs(worker) for worker in workers]
