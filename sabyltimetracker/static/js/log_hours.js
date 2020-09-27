//Returns a list of objects {'user': test, 'amount': 0} from
//the datatable. Only the rows with amount greater than 0 are added.
function get_datatable_info(table){
    let hours_list = [];
    let error = false;
    table.$('.hours-input').each(function (i, el) {
        let htmlElement = $(el);
        console.log(htmlElement.val());
        let hours = parseFloat(htmlElement.val());
        let workerCode = htmlElement[0].name;
        let comment = $('#'+workerCode+'-comment').val();

        if ($('#div-hours-many-workers').is(':visible')){
            if ($('#'+workerCode+'-select-many-workers').is(':checked')){
                console.log(workerCode + " - tiene check activo");
                hours = parseFloat($('#hours-many-workers').val());
                comment = $('#comment-many-workers').val();
            } else {
                console.log(workerCode + " - tiene check inactivo");
            }

        }

        //Se controla que las horas ingresadas sean múltiplo de 0.5
        if (hours*2%1!==0) {
            error = true;
        } else {
            if (htmlElement.attr('type') === 'checkbox'){
//                if (is_expected_eight_hours == true){
//                    hours = (htmlElement.prop('checked') ? 8 : 0);
//                } else {
//                    hours = (htmlElement.prop('checked') ? 9 : 0);
//                }

                console.log('expected: ' + expected);
                if (expected == 8){
                    console.log('expected es 8');
                    hours = (htmlElement.prop('checked') ? 8 : 0);
                } else {
                    console.log('expected es 9');
                    hours = (htmlElement.prop('checked') ? 9 : 0);
                }
            }
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
    const $select_many_workers = $('#select-many-workers');
    const $task = $('#task');
    const $task_category = $('#task-category');
    const $hours_label = $('.hours-label');
    const $hours_input = $('.hours-input');
    const $check_input = $('.check-input');
    const $submit_hours = $('#submit-hours');

    var require_prompt_on_task_change = false;
    var current_category = '';
    var current_task = '';

    $select_all.hide();
    $('[data-toggle="tooltip"]').tooltip();
    let table = $('#hours_per_user').DataTable( {
        "pageLength": 100,
        "lengthChange": false,
        "language": {
            "sProcessing": "Procesando...",
            "sLengthMenu": "Mostrar _MENU_ registros",
            "sZeroRecords": "No se encontraron resultados",
            "sEmptyTable": "Ningún dato disponible en esta tabla",
            "sInfo": "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
            "sInfoEmpty": "Mostrando registros del 0 al 0 de un total de 0 registros",
            "sInfoFiltered": "(filtrado de un total de _MAX_ registros)",
            "sInfoPostFix": "",
            "sSearch": "Buscar:",
            "sUrl": "",
            "sInfoThousands": ",",
            "sLoadingRecords": "Cargando...",
            "oPaginate": {
                "sFirst": "Primero",
                "sLast": "Último",
                "sNext": "Siguiente",
                "sPrevious": "Anterior"
            },
            "oAria": {
                "sSortAscending": ": Activar para ordenar la columna de manera ascendente",
                "sSortDescending": ": Activar para ordenar la columna de manera descendente"
            },
            "buttons": {
                "copy": "Copiar",
                "colvis": "Visibilidad"
            }
        }
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

//            if (task.category.toLowerCase().indexOf("especial") > -1){
//                console.log('task.category es especial');
//                let i = 0;
//                while (i < data.hours_list.length){
////                    let workerCode = data.hours_list[i].user;
////                    let input = $('#'+workerCode+'-hours');
//                    if (data.hours_list[i].amount > 0){
//                        if (data.hours_list[i].comment == ""){
////                            alert(COMMENT_REQUIRED_TXT + " - userId: " + data.hours_list[i].user + " - task_id: " + task.code);
////                            return false;
//                            /* Se setea codigo de la tarea de forma automatica en comentario de la tarea */
//                            data.hours_list[i].comment = task.code;
//                        }
//                    }
//                    i++;
//                }
//            } else {
//                console.log('task.category NO es especial');
//            }



            /** Comentario obligatorio **/
            if (task.requires_comment) {
                let i = 0;
                while (i < data.hours_list.length){
//                    let workerCode = data.hours_list[i].user;
//                    let input = $('#'+workerCode+'-hours');
                    if (data.hours_list[i].amount > 0){
                        if (data.hours_list[i].comment == ""){
//                            alert(COMMENT_REQUIRED_TXT + " - userId: " + data.hours_list[i].user + " - task_id: " + task.code);
//                            return false;
                            /* Se setea codigo de la tarea de forma automatica en comentario de la tarea */
                            /* Por ahora se quitan los comentarios obligatorios */
//                            data.hours_list[i].comment = task.code;
                        }
                    }
                    i++;
                }
            }
            /** Fin de Comentario obligatorio **/


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
        var keyText = $('#task-browser').val();
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
            var largo = grouped_tasks.length
            console.log("largo: " + largo)

            while (i < largo) {
                if (grouped_tasks[i].name === cat_name){
                    cat = grouped_tasks[i];
                    for (let j in cat.tasks) {
                        let task = cat.tasks[j];
                        if ((task.name.toLowerCase().indexOf(keyText.toLowerCase()) > -1) || (task.code.toLowerCase().indexOf(keyText.toLowerCase()) > -1)){
                            $('#'+task.id).show();
                        } else {
                            $('#'+task.id).hide();
                        }
                    }
                } else {
                    cat = grouped_tasks[i];
                    for (let j in cat.tasks) {
                        let task = cat.tasks[j];
                        $('#'+task.id).hide();
                    }

                }

                i++;
            }

            $task.prop('disabled', false);
        } else {

            for (let k in grouped_tasks) {
                let cat = grouped_tasks[k];
                for (let x in cat.tasks) {
                    let task = cat.tasks[x];
                    if ((task.name.toLowerCase().indexOf(keyText.toLowerCase()) > -1) || (task.code.toLowerCase().indexOf(keyText.toLowerCase()) > -1)){
                        $('#'+task.id).show();
                    } else {
                        $('#'+task.id).hide();
                    }
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
            if (jQuery.inArray(task.code, tasks_many_workers) !== -1) {
                $('#div-hours-many-workers').show();
                $('#th-hours-many-workers').show();
                $('.td-hours-many-workers').show();
                $hours_input.prop('disabled', true);
                $('.comentario').prop('disabled', true);
            } else {
                $('#div-hours-many-workers').hide();
                $('#th-hours-many-workers').hide();
                $('.td-hours-many-workers').hide();
                $hours_input.prop('disabled', false);
                $('.comentario').prop('disabled', false);
            }

            $submit_hours.prop('disabled', false);

            if(task.is_boolean) {
                $hours_input.attr('type', 'checkbox');
                $select_all.show();
                if ((task.logs) && (task.logs.length > 0)){
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
                if ((task.logs) && (task.logs.length > 0)){
                    for (let i in task.logs) {
                        let log = task.logs[i];
                        $('#'+log.worker.code+'-hours').val(log.amount);
                        $('#'+log.worker.code+'-comment').val(log.comment);
                    }
                    $submit_hours.text(UPDATE_HOURS_FOR_TXT+ ' ' + task.name);
                } else {
                    $submit_hours.text(LOG_HOURS_FOR_TXT +' '+ task.name);
                    for (let j in workers) {
                        let worker = workers[j];
                        $('#'+worker.code+'-comment').val('');
                    }
                }
                $hours_label.text(HOURS_FOR_TXT + ' ' + task.name);
            }
            if (task.requires_comment) {
                $('textarea').attr('placeholder', COMMENT_REQUIRED_TXT);
            } else {
                $('textarea').attr('placeholder', COMMENT_NOT_REQUIRED_TXT);
            }



            update_logged_hours(task.id);
        } else {
            $hours_label.text(SELECT_TASK_TXT);
            $hours_input.prop('disabled', true);
            $submit_hours.prop('disabled', true);
            $submit_hours.text(LOG_HOURS_TXT);
            update_logged_hours(null);
            $('.comentario').prop('disabled', true);
            $('#div-hours-many-workers').hide();
            $('#th-hours-many-workers').hide();
            $('.td-hours-many-workers').hide();
        }
    });

    $select_all.change( () => {
        $hours_input.prop('checked', $select_all.prop('checked'));
    });

    $select_many_workers.change( () => {
        $check_input.prop('checked', $select_many_workers.prop('checked'));
    });


    $hours_input.change( () => {
        require_prompt_on_task_change = true;
    });


    $('#task-browser').keyup(function(){

        var cat_name = $('#task-category').find(':selected').html();
        var keyText = $(this).val();

//        if (cat_name.toLowerCase().indexOf(("All categories").toLowerCase()) == -1){
        if (cat_name.toLowerCase().indexOf(("Todas las categ").toLowerCase()) == -1){
            for (let k in grouped_tasks) {
                if (grouped_tasks[k].name === cat_name){
                    let cat = grouped_tasks[k];
                    for (let x in cat.tasks) {
                        let task = cat.tasks[x];
                        if ((task.name.toLowerCase().indexOf(keyText.toLowerCase()) > -1) || (task.code.toLowerCase().indexOf(keyText.toLowerCase()) > -1)){
                            $('#'+task.id).show();
                        } else {
                            $('#'+task.id).hide();
                        }
                    }

                } else {
                    let cat = grouped_tasks[k];
                    for (let x in cat.tasks) {
                        let task = cat.tasks[x];
                        $('#'+task.id).hide();
                    }
                }
            }

        } else {
            for (let k in grouped_tasks) {

                let cat = grouped_tasks[k];
                for (let x in cat.tasks) {
                    let task = cat.tasks[x];
                    if ((task.name.toLowerCase().indexOf(keyText.toLowerCase()) > -1) || (task.code.toLowerCase().indexOf(keyText.toLowerCase()) > -1)){
                        $('#'+task.id).show();
                    } else {
                        $('#'+task.id).hide();
                    }
                }

            }

        }
    });

    $('#task-category').html($('#task-category').html().replace(">Special", ">Especial"));
    $('#task-category').html($('#task-category').html().replace(">All Categories", ">Todas las categorías"));

    $('.comentario').prop('disabled', true);


    $('#hours_per_user_paginate').click(function(){
        current_task = $('#task').val();
        let option = $('#task').find(":selected");
        let id = parseInt($(option).val());
        let task = find_task(id);

        if (task){
            $('.comentario').prop('disabled', false);
        } else {
            $('.comentario').prop('disabled', true);
        }
    });

});


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
//    let tareas_que_no_suman = ["AS", "CAP", "E", "FOCAP", "LS", "P", "POST", "S", "SA", "LL", "F", "FA"];
    let i, j;
    for (i in workers) {
        let worker = workers[i];
        let sum = 0;
        let sum_tarea_especial_todo_el_dia = 0;
        let tiene_tarea_especial_todo_el_dia = false
        for (j in worker.logs) {
            let log = worker.logs[j];
            // Si el codigo de tarea no pertenece al arreglo tareas_que_no_suman, se siguen sumando los logs
            if (jQuery.inArray(log.task.code, tareas_que_no_suman) == -1) {
                sum += log.amount;
            }
            // Si el codigo de tarea pertenece al arreglo tareas_especiales_todo_el_dia se obtiene las horas de logs
            if (jQuery.inArray(log.task.code, tareas_especiales_todo_el_dia) > -1) {
                sum_tarea_especial_todo_el_dia += log.amount;
                tiene_tarea_especial_todo_el_dia = true;
            }
        }

        if (tiene_tarea_especial_todo_el_dia){
            $('#'+worker.code+'-logged-hours').text(sum_tarea_especial_todo_el_dia);
        } else {
            $('#'+worker.code+'-logged-hours').text(sum);
        }
    }
    let $logged_hours_label = $('.logged-hours-label');
    if(excluded_task_id)
        $logged_hours_label.text(HOURS_OTHER_TASKS_TXT);
    else
        $logged_hours_label.text(TOTAL_HOURS_TXT);

}


//function disabled_enabled_comment_buttons(){
//    $('.comentario').each(function (i) {
//        let idDataTarget = $(this).attr('data-target');
//        let arr = idDataTarget.split("-");
//        let idWorker = arr[0];
//
//        if ($(idWorker + '-hours').val() == 0){
//            $(this).attr('disabled', true);
//        }
//    });
//}
