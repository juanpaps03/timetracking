//Returns a list of objects {'user': test, 'amount': 0} from
//the datatable. Only the rows with amount greater than 0 are added.
function get_datatable_info(table){
    let hours_list = [];
    let error = false;
    table.$('input').each(function (i, el) {
        let htmlElement = $(el);
        let hours = parseFloat(htmlElement.val());
        let workerCode = htmlElement[0].name;
        let comment = $('#'+workerCode+'-comment').val();
        if (hours*2%1!==0) {
            error = true;
        } else {
            if (htmlElement.attr('type') === 'checkbox')
                hours = (htmlElement.prop('checked') ? 9 : 0);
            let userId = htmlElement.attr('name');
            hours_list.push({'user': userId, 'amount': hours, 'comment':comment});
        }
    });
    if (!error)
        return hours_list;
    return false;
}

$(document).ready(function() {
    const $select_all = $('#select-all');
    const $task = $('#task');
    const $task_category = $('#task-category');
    const $hours_label = $('.hours-label');
    const $hours_input = $('.hours-input');
    const $submit_hours = $('#submit-hours');
    const $comment_group = $('#comment-group');
//    const $comment = $('#comment');

    var require_prompt_on_task_change = false;
    var current_category = '';
    var current_task = '';

    $select_all.hide();
    //$comment_group.hide();
    $('[data-toggle="tooltip"]').tooltip();
    let table = $('#hours_per_user').DataTable( {
        "pageLength": 10
    });

    update_logged_hours(null);

    $submit_hours.click( function() {
        let taskId = parseInt($task.val());
        let hoursList = get_datatable_info(table);
//        let comment = $comment.val();

        let task = find_task(taskId);

        let data = {'task': taskId, 'hours_list': hoursList};

        // csrf and post_url are rendered in server side and
        // are defined in log_hours.html javascript_header section
        if (data.hours_list && data.hours_list.length > 0) {



            if (task.requires_comment) {
                let i = 0;
                while (i < data.hours_list.length){

//                    let workerCode = data.hours_list[i].user;
//                    let input = $('#'+workerCode+'-hours');

                    if (data.hours_list[i].amount > 0){
                        if (data.hours_list[i].comment == ""){
                            alert(COMMENT_REQUIRED_TXT + " - userId: " + data.hours_list[i].user);
                            return false;
                        }
                    }


                    i++;
                }


            }



//            if (task.requires_comment && !comment) {
//                let hour_sum = 0;
//                for (i in data.hours_list) {
//                    hour_sum += data.hours_list[i].amount;
//
//                    if (data.hours_list[i].amount > 0){
//                        console.log('userId: ' + data.hours_list[i].user + ' - amount: ' + data.hours_list[i].amount);
//                        console.log('la fila ' + i +' tiene comentario.');
//                    } else {
//                        console.log('userId: ' + data.hours_list[i].user + ' - amount: ' + data.hours_list[i].amount);
//                        console.log('la fila ' + i +' NO tiene comentario.');
//                    }
//
//                }
//                if (hour_sum > 0) {
//                    alert(COMMENT_REQUIRED_TXT);
//                    return false;
//                }
//            }
            $.ajaxSetup({
                headers: { "X-CSRFToken": csrf }
            });
            $.ajax({
              type : "POST",
              url : post_url,
              data : JSON.stringify(data),
              headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
                },
              success: function(){
                  location.reload();
                },
              error: function(XMLHttpRequest, textStatus, errorThrown) {
                alert("ERROR: " + String(errorThrown) + " - " + String(textStatus) + " - " + String(XMLHttpRequest.responseText));
                return false;
                }
            });
        } else {
            alert(WRONG_PRECISION_TXT);
            return false;
        }

        return true;
    });

    $task_category.change( () => {
        let change_confirmed = !require_prompt_on_task_change || confirm(TASK_CHANGE_PROMPT);
        if (!change_confirmed) {
            $task_category.val(current_category);
            return
        }
        current_category = $task_category.val();
        require_prompt_on_task_change = false;

        let option = $task_category.find(':selected');
        let cat_name = $(option).val();
        if (cat_name) {
            let cat = null;
            let i = 0;
            while (!cat) {
                if (grouped_tasks[i].name === cat_name)
                    cat = grouped_tasks[i];
                i++;
            }
            $task.html('');
            $task.append('<option value="">-' + SELECT_TASK_TXT + '-</option>');
            for (let j in cat.tasks) {
                let task = cat.tasks[j];
                $task.append('<option value="' + task.id + '">' + task.code + ' - ' + task.name + '</option>');
            }
            $task.prop('disabled', false);
        } else {
            $task.html('');
            $task.append('<option value="">-' + SELECT_TASK_TXT + '-</option>');
            for (let i in grouped_tasks) {
                let cat = grouped_tasks[i];
                for (let j in cat.tasks) {
                    let task = cat.tasks[j];
                    $task.append('<option value="' + task.id + '">' + task.code + ' - ' + task.name + '</option>');
                }
            }
        }
        $task.change();
    });

    $task.change( () => {
        let change_confirmed = !require_prompt_on_task_change || confirm(TASK_CHANGE_PROMPT);
        if (!change_confirmed) {
            $('#task').val(current_task);
            return
        }
        current_task = $('#task').val();
        require_prompt_on_task_change = false;

        let option = $('#task').find(":selected");
        let id = parseInt($(option).val());
        let task = find_task(id);
        $hours_input.attr('type', 'number');
        $select_all.hide();
        $hours_input.val(0);
        $hours_input.prop('checked', false);
        if (task) {
            $hours_input.prop('disabled', false);
            $submit_hours.prop('disabled', false);
            if(task.is_boolean) {
                $hours_input.attr('type', 'checkbox');
                $select_all.show();
                if (task.logs) {
                    for (let i in task.logs) {
                        let log = task.logs[i];
                        $('#'+log.worker.code+'-hours').prop('checked', true);
                        $('#'+ log.worker.code +'-comment').val(log.comment);

                    }
                    $submit_hours.text(UPDATE_BOOLEAN_TASK_TXT+ ' '+ task.name);
                } else {
                    $submit_hours.text(LOG_BOOLEAN_TASK_TXT+ ' '+ task.name);
                }
                $hours_label.text(task.name);
            } else {
                if (task.logs) {
                    for (let i in task.logs) {
                        let log = task.logs[i];
                        $('#'+log.worker.code+'-hours').val(log.amount);
                        $('#'+log.worker.code+'-comment').val(log.comment);
                    }
                    $submit_hours.text(UPDATE_HOURS_FOR_TXT+ ' ' + task.name);
                } else {
                    $submit_hours.text(LOG_HOURS_FOR_TXT +' '+ task.name);
                }
                $hours_label.text(HOURS_FOR_TXT + ' ' + task.name);
            }
            if (task.requires_comment) {
                //$comment_group.show();
                $('textarea').attr('placeholder', COMMENT_REQUIRED_TXT);
            } else {
                //$comment_group.hide();
                $('textarea').attr('placeholder', COMMENT_NOT_REQUIRED_TXT);
            }



            update_logged_hours(task.id);
        } else {
            $hours_label.text(SELECT_TASK_TXT);
            $hours_input.prop('disabled', true);
            $submit_hours.prop('disabled', true);
            $submit_hours.text(LOG_HOURS_TXT);
            update_logged_hours(null);
        }
    });

    $select_all.change( () => {
        $hours_input.prop('checked', $select_all.prop('checked'));
    });

    $hours_input.change( () => {
        require_prompt_on_task_change = true;
    });
} );


function find_task(task_id) {
    let task = null;
    let i = 0;
    while (task==null && i < tasks.length) {
        if (task_id === tasks[i].id)
            task = tasks[i];
        i++;
    }
    return task;
}

function update_logged_hours(excluded_task_id) {
    let i, j;
    for (i in workers) {
        let worker = workers[i];
        let sum = 0;
        for (j in worker.logs) {
            let log = worker.logs[j];
            //if (log.task.id !== excluded_task_id && !log.task.is_boolean)
                sum += log.amount;
        }
        $('#'+worker.code+'-logged-hours').text(sum);
    }
    let $logged_hours_label = $('.logged-hours-label');
    if(excluded_task_id)
        $logged_hours_label.text(HOURS_OTHER_TASKS_TXT);
    else
        $logged_hours_label.text(TOTAL_HOURS_TXT);

}


