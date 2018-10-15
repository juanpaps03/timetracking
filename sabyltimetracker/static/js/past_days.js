$(document).ready(function() {
    $('#day').change( () => {
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
    });

    $('#edit').click( () => {
        let option = $(this).find(":selected");
        let v = $(option).attr('data-url');
        window.location.href = v;
    });
} );
