/**
 * Created by yexiaoxing on 6/29/16.
 */
var validity = 0;
var validitied_email = "";
$(document).ready(function () {
    var MAIL_CHECK_API = "/api/check_email";
    $("#email").blur(function (e) {
        document.getElementById('email').checkValidity();
        if (document.getElementById('email').validity.valid) {
            remove_error_class($("#email-error").html("").parent());
            check_username_ajax($("#email").val());
        } else {
            add_error_class($("#email-error").html("Invalid email address.").parent());
        }
    });

    function check_username_ajax(email_data, callback) {
        $.ajax({
            contentType: 'application/json',
            method: "POST",
            url: MAIL_CHECK_API,
            data: JSON.stringify({ 'email': email_data })
        })
            .done(function (data) {
                callback = typeof callback !== 'undefined' ? callback : jQuery.noop;
                //uncomment the line below to inspect the response in js console/firebug etc
                console.log(data);
                validitied_email = data.email;
                if (data.code == 200) {
                    validity = 1;
                    remove_error_class($("#email-error").html(data.message).parent());
                } else {
                    validity = 2;
                    add_error_class($("#email-error").html(data.message).parent());
                }
                callback();
            }, "json");
    }

    function add_error_class(node) {
        node.addClass("has-error");
    }

    function remove_error_class(node) {
        node.removeClass("has-error");
    }

    $("form").submit(function (event) {
        console.log("Form submitting... Email validity:" + validity);
        if (validity == 2) {
            event.preventDefault();
            if (validitied_email != $('#email').val()) {
                check_username_ajax($("#email").val(), $("form").submit);
            }
        } else if (validity == 0) {
            event.preventDefault();
            check_username_ajax($("#email").val(), $("form").submit);
        }
        if ($('#password2').val() != $('#password').val()) {
            event.preventDefault();
            add_error_class($('#password-error').html('Passwords must match.').parent());
            console.log("Password mismatch.")
        }
        $.each(required_field, function (index, field_id) {
            if ($(field_id).val() == "") {
                event.preventDefault();
                add_error_class($(field_id + "-error").html("This field is required.").parent());
            }
        })
    });

    var required_field = ['#email', '#firstname', '#lastname', '#password', '#password2', '#organization', '#code', '#location'];

    $.each(required_field, function (index, field_id) {
        $(field_id).attr("placeholder", $(field_id).attr("placeholder") + " *")
    })
});

