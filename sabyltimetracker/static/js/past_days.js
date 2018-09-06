$(document).ready(function() {
    $('#day').change( () => {
        let option = $(this).find(":selected");
        let v = $(option).val();
        const $next = $('#next');
        if(v) {
            $next.prop('disabled', false);
        } else {
            $next.prop('disabled', true);
        }
    });
    $('#next').click( () => {
        let option = $(this).find(":selected");
        let v = $(option).val();
        window.location.href = v;
    });
} );
