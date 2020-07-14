


$(document).ready(function() {
    /*$('#day').change( () => {
        let option = $(this).find(":selected");
        $option = $(option);
        let url = $option.attr('data-url');
        const $edit = $('#edit');
        const $report = $('#report');
        if(url) {
            $report.prop('disabled', false);
            $edit.prop('disabled', false);
        } else {
            $edit.prop('disabled', true);
            if ($option.val())
                $report.prop('disabled', false);
            else
                $report.prop('disabled', true);
        }
    });*/



    /*$('#edit').click( () => {
        let option = $(this).find(":selected");
        let v = $(option).attr('data-url');
        window.location.href = v;
    });*/




    $('#report').click(function(){

        $('#loading').addClass('is-active');

        let workdaydate = $('#selectDay').val();

        let obra = $('#obraSelect').children("option:selected").val();

        console.log('obra:');
        console.log(obra);
        console.log('workdaydate:');
        console.log(workdaydate);


        //llamada con fetch
        let datos = {'workdaydate': workdaydate, 'obra': obra};
        var myHeaders = new Headers({
              'X-CSRFToken': csrf,
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            });

        var myInit = { method: 'POST',
                       headers: myHeaders,
                       body: JSON.stringify(datos)};

        fetch(post_url, myInit)
        .then(function(response) {
            if(response.ok) {
                console.log(response);
                var filename = 'reporte';
                var disposition = response.headers.get('Content-Disposition');
                if (disposition && disposition.indexOf('attachment') !== -1) {
                    var filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
                    var matches = filenameRegex.exec(disposition);
                    if (matches != null && matches[1]) filename = matches[1].replace(/['"]/g, '');
                }
                console.log('filename: ' + filename);

                response.blob().then(function(blob) {
                    console.log(blob);
                    var downloadUrl = URL.createObjectURL(blob);
                    var a = document.createElement("a");
                    a.href = downloadUrl;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    $('#loading').removeClass('is-active');
                    $('#div-mensaje-error').hide();
                });
            } else {
                response.json().then(function(respuesta) {
                    console.log(respuesta);
                    console.log('Respuesta de red OK pero respuesta HTTP no OK');
                    $('#loading').removeClass('is-active');
                    $('#div-mensaje-error').show();
                    $('#mensaje-error').html(respuesta.message);
                });
            }
        })
        .catch(function(error) {
          console.log('Hubo un problema con la petición Fetch:' + error.message);
          $('#loading').removeClass('is-active');
          $('#div-mensaje-error').show();
          $('#mensaje-error').html("Intente nuevamente.");
        });
        //fin llamada con fetch

    });


});





















