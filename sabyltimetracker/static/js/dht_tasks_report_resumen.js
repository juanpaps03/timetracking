
    $('#initialDay').datepicker({
        closeText: "Cerrar",
        prevText: "&#x3C;Ant",
        nextText: "Sig&#x3E;",
        currentText: "Hoy",
        monthNames: [ "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre" ],
        monthNamesShort: [ "ene","feb","mar","abr","may","jun",
        "jul","ago","sep","oct","nov","dic" ],
        dayNames: [ "domingo","lunes","martes","miércoles","jueves","viernes","sábado" ],
        dayNamesShort: [ "dom","lun","mar","mié","jue","vie","sáb" ],
        dayNamesMin: [ "D","L","M","MI","J","V","S" ],
        weekHeader: "Sm",
        dateFormat: "dd/mm/yy",
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: ""
    });
    $('#finishDay').datepicker({
        closeText: "Cerrar",
        prevText: "&#x3C;Ant",
        nextText: "Sig&#x3E;",
        currentText: "Hoy",
        monthNames: [ "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre" ],
        monthNamesShort: [ "ene","feb","mar","abr","may","jun",
        "jul","ago","sep","oct","nov","dic" ],
        dayNames: [ "domingo","lunes","martes","miércoles","jueves","viernes","sábado" ],
        dayNamesShort: [ "dom","lun","mar","mié","jue","vie","sáb" ],
        dayNamesMin: [ "D","L","M","MI","J","V","S" ],
        weekHeader: "Sm",
        dateFormat: "dd/mm/yy",
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: ""
    });
    $('#finishBiweeklyDay').datepicker({
        closeText: "Cerrar",
        prevText: "&#x3C;Ant",
        nextText: "Sig&#x3E;",
        currentText: "Hoy",
        monthNames: [ "enero","febrero","marzo","abril","mayo","junio",
        "julio","agosto","septiembre","octubre","noviembre","diciembre" ],
        monthNamesShort: [ "ene","feb","mar","abr","may","jun",
        "jul","ago","sep","oct","nov","dic" ],
        dayNames: [ "domingo","lunes","martes","miércoles","jueves","viernes","sábado" ],
        dayNamesShort: [ "dom","lun","mar","mié","jue","vie","sáb" ],
        dayNamesMin: [ "D","L","M","MI","J","V","S" ],
        weekHeader: "Sm",
        dateFormat: "dd/mm/yy",
        firstDay: 1,
        isRTL: false,
        showMonthAfterYear: false,
        yearSuffix: ""
    });

    $("#finishDay").datepicker("option", "disabled", true);

    $("#finishBiweeklyDay").change(function(){
      let valor = $("#finishBiweeklyDay").val();
      console.log("valor: " + valor)
      if ((valor != null) && (valor != "")){
        $("#finishDay").datepicker("option", "disabled", false);
      } else {
        $("#finishDay").datepicker("option", "disabled", true);
      }
    });



    $(document).ready(function(){

        $('#report').click(function(){

            $('#loading').addClass('is-active');

            let initialDay = $('#initialDay').val();
            let finishBiweeklyDay = $('#finishBiweeklyDay').val();
            let finishDay = $('#finishDay').val();
            if (typeof finishDay === "undefined") {
            finishDay = '';
            }
            let obra = $('#obra').children("option:selected").val();

            console.log('obra:');
            console.log(obra);


            //llamada con fetch
            let datos = {'initialDay': initialDay, 'finishBiweeklyDay': finishBiweeklyDay, 'finishDay': finishDay, 'obra': obra};
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










