function onChange(el) {
    if (typeof Event === 'function' || !document.fireEvent) {
        var event = document.createEvent('HTMLEvents');
        event.initEvent('change', true, true);
        el.dispatchEvent(event);
    } else {
        el.fireEvent('onchange');
    }
}


$(document).ready(function () {

    // clipboard
    var clipboard = new Clipboard(document.getElementById("url_copy_btn"));
    clipboard.on('success', function (e) {
        $('#url_copy_btn').tooltip({title: "Copied!"});
        $('#url_copy_btn').tooltip('show');
        e.clearSelection();
    });
    clipboard.on('error', function (e) {
        $('#url_copy_btn').tooltip({title: "Press Ctrl+C to copy"});
        $('#url_copy_btn').tooltip('show');
    });

    // initialize switchery  javascript
    var elems = Array.prototype.slice.call(document.querySelectorAll('.switch-button'));
    elems.forEach(function (elem) {
        if (elem.getAttribute("name") === "disabled") {
            var switchery = new Switchery(elem, {color: '#1AB394', size: 'large', disabled: true});
        } else {
            var switchery = new Switchery(elem, {color: '#1AB394', size: 'large'});
        }
    });


    $('#registration_switch').change(function (event) {
        var result = document.getElementById('registration_switch').checked;
        $.ajax({
            type: "POST",
            url: "/setregistration",
            data: {
                conference_id: conferenceID, 
                registration_status: result
            },
            success: function (response) {
                // console.log(response);
                // if (result) {
                //     // $('#registration_setting').show();
                // } else {
                //     // $('#registration_setting').hide();
                // }
            }, // end of success
            complete: function (xhr, textStatus) {
                if (xhr.status === 403 || xhr.status === 500) {
                    document.getElementById('registration_switch').checked = false;
                    onChange(document.getElementById('registration_switch'));
                    swal({
                        title: "Oops...",
                        text: "Add at least one ticket before open registration",
                        type: "error"
                    });
                }
            }
        });
    });


}); //end of ready