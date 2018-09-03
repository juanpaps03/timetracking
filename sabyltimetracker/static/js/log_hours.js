//Returns a list of objects {'user': test, 'amount': 0} from
//the datatable. Only the rows with amount greater than 0 are added.
function get_datatable_info(table){
    var hours_list = [];
    table.$('input').each(function (i, el) {
       var htmlElement = $(el);
       var hours = parseFloat(htmlElement.val());
       var userId = htmlElement.attr('name');

       if (hours > 0){
          hours_list.push({'user': userId, 'amount': hours});
       }
    });

    return hours_list;
}

$(document).ready(function() {
    var table = $('#hours_per_user').DataTable();

    $('#submit-hours').click( function() {
        var taskId = $('#task').val();
        var hoursList = get_datatable_info(table);

        var data = {'task': taskId, 'hours_list': hoursList};

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
        var option = $(this).find(":selected");
        var name = $(option).attr('data-name');
        if(name) {
            $('.hours-label').text('Hours for ' + name);
            // TODO translation
            $('.hours-input').prop('disabled', false);
        } else {
            $('.hours-label').text('Select a task');
            $('.hours-input').prop('disabled', true);
        }
    });
} );
