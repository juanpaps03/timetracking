//Returns a list of objects {'user': test, 'amount': 0} from
//the datatable. Only the rows with amount greater than 0 are added.
function get_datatable_info(table){
    let hours_list = [];
    table.$('input').each(function (i, el) {
        let htmlElement = $(el);
        let hours = parseFloat(htmlElement.val());
        if (htmlElement.attr('type') === 'checkbox')
            hours = (htmlElement.prop('checked') ? 1 : 0);
        let userId = htmlElement.attr('name');
        hours_list.push({'user': userId, 'amount': hours});
    });

    return hours_list;
}

$(document).ready(function() {
    $('[data-toggle="tooltip"]').tooltip();
    let table = $('#hours_per_user').DataTable();

    update_logged_hours(null);

    $('#submit-hours').click( function() {
        let taskId = $('#task').val();
        let hoursList = get_datatable_info(table);

        let data = {'task': taskId, 'hours_list': hoursList};

        // csrf and post_url are rendered in server side and
        // are defined in log_hours.html javascript_header section
        if (typeof data.hours_list !== 'undefined' && data.hours_list.length > 0) {
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
                alert("some error " + String(errorThrown) + String(textStatus) + String(XMLHttpRequest.responseText));
                return false;
                }
            });
        } else {
            alert("No information to send.");
            return false;
        }

        return true;
    } );
    $('#task').change( () => {
        let option = $(this).find(":selected");
        let id = parseInt($(option).val());
        let task = find_task(id);
        const $hours_label = $('.hours-label');
        const $hours_input = $('.hours-input');
        const $submit_hours = $('#submit-hours');
        $hours_input.attr('type', 'text');
        $hours_input.val(0);
        $hours_input.prop('checked', false);
        if(task) {
            $hours_input.prop('disabled', false);
            $submit_hours.prop('disabled', false);
            if(task.code !== absence_code) {
                if (task.logs) {
                    for (let i in task.logs) {
                        let log = task.logs[i];
                        $('#'+log.worker.code+'-hours').val(log.amount);
                    }
                    $submit_hours.text(UPDATE_HOURS_FOR_TXT+ ' ' + task.name);
                } else {
                    $submit_hours.text(LOG_HOURS_FOR_TXT +' '+ task.name);
                }
                $hours_label.text(HOURS_FOR_TXT + ' ' + task.name);
            } else {
                $hours_input.attr('type', 'checkbox');
                if (task.logs) {
                    for (let i in task.logs) {
                        let log = task.logs[i];
                        $('#'+log.worker.code+'-hours').prop('checked', true);
                    }
                    $submit_hours.text(UPDATE_ABSENCES_TXT);
                } else {
                    $submit_hours.text(LOG_ABSENCES_TXT);
                }
                $hours_label.text(ABSENCES_TXT);
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
            if (log.task.id !== excluded_task_id && log.task.code !== absence_code)
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


