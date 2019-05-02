function add_ticket() {
    numTickets++;

    var template = $('#ticket_template').children().clone();
    template.addClass('add-ticket');
    template.addClass('ticket_group');
    template.attr('id', 'ticket_' + numTickets);
    template.find('label').text('Ticket ' + numTickets);
    template.find('.ticket-title').attr('name', 'ticket_title_' + numTickets);
    template.find('.ticket-price').attr('name', 'ticket_price_' + numTickets);
    template.find('.setting').attr('data-target', '#ticket_collapse_' + numTickets);
    template.find('.collapse').attr('id', 'ticket_collapse_' + numTickets);
    template.find('input[name=\'start\']').attr('value', get_today());

    if (new Date() > new Date(conferenceEndDate)) {
        template.find('input[name=\'end\']').attr('value', get_today());
    } else {
        template.find('input[name=\'end\']').attr('value', conferenceEndDate);
    }
    $('#ticket-container').append(template);
    init_datepicker($('.input-daterange'), new Date());
}

function set_ticket_status(id, status) {
    $.ajax({
        type: "PUT",
        url: "/setticketstatus",
        data: {ticket_id: id, ticket_status: status},
        success: function (response) {
            // console.log(response);
        }
    });
}

function radio_checked(element) {
    var limit_input = document.getElementsByName("quantity")[0];
    if (element.id === "usage_limit_type_with_limit") {
        limit_input.disabled = false;
        limit_input.required = true;
    } else {
        limit_input.disabled = true;
        limit_input.required = false;
        if (d = document.getElementById("quantity-error")) d.style.display = "none";
    }
}

function onChange(el) {
    if (typeof Event === 'function' || !document.fireEvent) {
        var event = document.createEvent('HTMLEvents');
        event.initEvent('change', true, true);
        el.dispatchEvent(event);
    } else {
        el.fireEvent('onchange');
    }
}

function option_convert(option) {
    // convert string into array
    if (typeof option === 'string') {
        // console.log(option);
        option = option.replace(/[\']/g, '\"');
        // console.log(option);
        // console.log(jQuery.type(JSON.parse(option)));
        return JSON.parse(option);
    } else {
        return option;
    }
}

function init_datepicker(selector, today) {
    selector.datepicker({
        keyboardNavigation: false,
        forceParse: false,
        autoclose: true,
        format: "yyyy-mm-dd",
        // beforeShowDay: function (date) {
        //     if (date < today) {
        //         return false;
        //     } else {
        //         return true;
        //     }
        // }
    }).on('hide', function (e) {
        e.stopPropagation();
    });
}

function get_today() {
    var d = new Date();
    return [d.getFullYear(), d.getMonth() + 1, d.getDate()].join('-');
}

function usage_limit(element) {
    var with_limit = document.getElementById("usage_limit_type_with_limit");
    element.value = parseInt(element.value, 10);
    with_limit.value = element.value;
    element.required = true;
}

function floatToString(num) {
    if (num.toString().indexOf('.') === -1) {
        return num.toFixed(1);
    } else {
        return num;
    }
}

function checkDuplicateInArray(a) {
    var counts = [];
    for (var i = 0; i <= a.length; i++) {
        if (counts[a[i]] === undefined) {
            counts[a[i]] = 1;
        } else {
            return true;
        }
    }
    return false;
}

function update_promo_code_info(promo_code, element) {
    // update promo code <tr>
    // console.log(promo_code);
    // update type
    element.find('promo-type').attr('value', promo_code.type);

    // update status
    element.find('.project-status > span').html(promo_code.status).toggleClass('label-primary label-default');

    // update promo-status button
    if (promo_code.status === 'Inactive') {
        element.find('.project-actions > .promo-status').attr('data-action', 'enable').html('Enable');
        element.find('.project-status > span').removeClass('label-primary').addClass('label-default');
    } else {
        element.find('.project-actions > .promo-status').attr('data-action', 'disable').html('Disable');
        element.find('.project-status > span').removeClass('label-default').addClass('label-primary');
    }

    // update promo code
    element.find('.promo-code').html(promo_code.promo_code);
    if (promo_code.type === 'fixed_amount') {
        element.find('.project-title small:eq(0)').html(floatToString(promo_code.value) + ' off');
    } else {
        element.find('.project-title small:eq(0)').html(floatToString(promo_code.value) + '% off');
    }
    // update promo currency
    element.find('.project-title small:eq(1)').html(' - only works on ' + promo_code.currency);
    element.find('.project-title small:eq(1)').attr('data-promo-code-currency', promo_code.currency);
    // update value
    element.find('.project-title small:eq(0)').attr('data-promo-code-value', promo_code.value);
    // update quantity
    element.find('.project-completion > small').attr({
        'data-promo-code-usage': promo_code.usage,
        'data-promo-code-quantity': promo_code.quantity
    });

    if (promo_code.quantity !== -1) {
        element.find('.project-completion > small').html(promo_code.usage + ' / ' + promo_code.quantity);
        element.find('.progress-bar').css('width', 100 * promo_code.usage / promo_code.quantity + '%');
    } else {
        element.find('.project-completion > small').html(promo_code.usage + ' / ' + 'Unlimited');
        element.find('.progress-bar').css('width', '0.0%');
    }

    // update date range
    element.find('.project-people > div')
        .html(promo_code.start_date + " ~ " + promo_code.end_date)
        .attr({
            'data-promo-code-start-date': promo_code.start_date,
            'data-promo-code-end-date': promo_code.end_date
        });
}

function render_new_promo_code(promo_code_info) {
    // console.log(promo_code_info);
    var list_td = document.getElementsByClassName("promo-codes-list")[0];

    var count = 1;
    while (document.getElementById("promo_" + count) != null) count++;

    // new tr
    var new_promo_tr = $(list_td.insertRow(list_td.rows.length));
    new_promo_tr.attr("id", "promo_" + count);

    // new input for type
    var promo_type = $("<input>");
    promo_type.attr({
        "type": "hidden",
        "class": "promo-type",
        "value": promo_code_info.type
    });

    // promo status
    var promo_status = $("<span>");
    promo_status.addClass("label label-primary").html("Active");
    var promo_status_container = $("<td>");
    promo_status_container.addClass("project-status").append(promo_status);

    // promo code and description
    var promo_code_container = $("<td>");
    promo_code_container.addClass("project-title");

    var promo_code = $("<div>");
    promo_code.addClass("promo-code").html(promo_code_info.promo_code);

    var promo_code_br = $("<br>");
    var promo_code_desc = $("<small>");
    promo_code_desc.attr("data-promo-code-value", promo_code_info.value);
    if (promo_code_info.type === "fixed_amount") {
        promo_code_desc.html(promo_code_info.value + " off");
    } else {
        promo_code_desc.html(promo_code_info.value + "% off");
    }
    var promo_code_currency = $("<small>");
    promo_code_currency.attr("data-promo-code-currency", promo_code_info.currency);
    promo_code_currency.html(" - only works on " + promo_code_info.currency);
    promo_code_container.append(promo_code).append(promo_code_br).append(promo_code_desc).append(promo_code_currency);

    // promo quantity
    var promo_quantity_container = $("<td>");
    promo_quantity_container.addClass("project-completion");
    var promo_quantity = $("<small>");
    promo_quantity.attr({
        "data-promo-code-usage": "0",
        "data-promo-code-quantity": promo_code_info.quantity
    });

    if (promo_code_info.quantity !== -1) {
        promo_quantity.html("0 / " + promo_code_info.quantity);
    } else {
        promo_quantity.html("0 / Unlimited");
    }
    var promo_quantity_bar_container = $("<div>");
    promo_quantity_bar_container.addClass("progress progress-mini");
    var promo_quantity_bar = $("<div>");
    promo_quantity_bar.attr({
        "class": "progress-bar",
        "style": "width: 0.0%;"
    });
    promo_quantity_bar_container.append(promo_quantity_bar);
    promo_quantity_container.append(promo_quantity).append(promo_quantity_bar_container);

    // promo date range
    var promo_date_range_container = $("<td>");
    promo_date_range_container.addClass("project-people");
    var promo_date_range = $("<div>");
    promo_date_range.attr({
        "data-promo-code-start-date": promo_code_info.start_date,
        "data-promo-code-end-date": promo_code_info.end_date
    }).html(promo_code_info.start_date + ' ~ ' + promo_code_info.end_date);

    promo_date_range_container.append(promo_date_range);

    // promo actions
    var promo_date_action_container = $("<td>");
    promo_date_action_container.addClass("project-actions");
    var disable_button = $("<button>");
    disable_button.addClass("btn btn-white btn-sm promo-status").html("Disable").attr({
        "data-promo-code-id": promo_code_info.id,
        "data-action": "disable"
    }).css({
        "position": "relative",
        "left": "-4px"
    });

    var edit_button = $("<button>");
    edit_button.addClass("btn btn-white btn-sm promo-edit").attr({
        "data-promo-code-id": promo_code_info.id,
        "data-action": "promo_code_edit",
        "data-target": "#promoCodeForm",
        "data-toggle": "modal"
    });

    var edit_icon = $("<i>");
    edit_icon.addClass("fa fa-pencil");
    edit_button.append(edit_icon).html('<i class="fa fa-pencil"></i> Edit ');

    promo_date_action_container.append(disable_button).append(edit_button);

    // add all
    new_promo_tr
        .append(promo_type)
        .append(promo_status_container)
        .append(promo_code_container)
        .append(promo_quantity_container)
        .append(promo_date_range_container)
        .append(promo_date_action_container);
}

function get_price(element) {
    var prices = {};
    $(element).find(".price_group").each(function (index) {
        prices[$(this).find("select").val()] = $(this).find("input").val();
    });
    return prices;
}

$(document).ready(function () {
    $("#ticket-container").delegate(".add_price", "click", function () { // add new price
        $(this.parentNode.parentNode.parentNode).append($("#price_template").children().clone());
    }).delegate(".remove_price", "click", function () {  // Remove a price
        $(this.parentNode.parentNode).remove();
    }).delegate('input', 'change', function (event) {   // Count existing tickets with changed title or price
        var form_group_div;
        if ($(this).hasClass('ticket-title')) {
            form_group_div = $(this).parent().parent().parent();
        } else if ($(this).hasClass('ticket-price')) {
            form_group_div = $(this).parent().parent().parent().parent();
        } else {
            form_group_div = $(this).parent().parent().parent().parent().parent().parent().parent();
        }

        if (form_group_div.hasClass('origin-ticket')) form_group_div.addClass('change-ticket');
        // console.log($(this).parent().parent());
    }).delegate('.status', 'click', function (event) {
        if ($(this).data('ticket-id') !== '') {
            if ($(this).hasClass('unconceal')) {
                $(this).toggleClass('conceal unconceal');
                $(this).find('i').toggleClass('fa-eye fa-eye-slash');
                set_ticket_status($(this).data('ticket-id'), 'Hided');
            } else {
                $(this).toggleClass('conceal unconceal');
                $(this).find('i').toggleClass('fa-eye fa-eye-slash');
                set_ticket_status($(this).data('ticket-id'), 'Normal');
            }
        }
    }).delegate('.remove', 'click', function (event) {
        if ($(this).data('ticket-id') !== '') {
            $(this).parent().parent().parent().addClass('remove-ticket');
            $(this).parent().parent().parent().css('display', 'none');
        } else {
            $(this).parent().parent().parent().remove();
        }
        numTickets--;
    });

    jQuery.validator.addMethod("positive_number", function (value, el, param) {
        return value >= 0;
    }, "The input value must be positive");
    jQuery.validator.classRuleSettings.positive_number = {positive_number: true, required: true};
    jQuery.validator.addMethod("currency_inequal", function (value, element) {
        var currency_list = [];
        $(element).find('.currency').each(function (index, element) {
            currency_list.append(element.value())
        });
        return true;
    }, "Please specify the correct domain for your documents");

    $('#setRegistration').validate({
        errorPlacement: function (error, element) {
            if (element.hasClass('ticket-price') || element.parent().hasClass('input-daterange') || element.parent().hasClass('input-group')) {
                error.insertAfter(element.parent());
            } else {
                error.insertAfter(element);
            }
            if (element.parent().hasClass('input-group')) {
                element.parent().addClass('error');
            }
        },
        highlight: function (element, errorClass, validClass) {
            if ($(element).parent().hasClass('input-group')) {
                $(element).parent().addClass(errorClass).removeClass(validClass);
            } else {
                $(element).addClass(errorClass).removeClass(validClass);
            }
        },
        unhighlight: function (element, errorClass, validClass) {
            if ($(element).parent().hasClass('input-group')) {
                $(element).parent().removeClass(errorClass).addClass(validClass);
            } else {
                $(element).removeClass(errorClass).addClass(validClass);
            }
        },
        rules: {
            ticket_group: {
                currency_inequal: true
            },
            positive_number: {
                positive_number: true,
                required: true
            }
        }
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

    // initialize datepicker jquery
    // get the current day
    var today = new Date();
    // add init start date
    $(".add-ticket input[name='start']").val(get_today());
    init_datepicker($('.input-daterange'), get_today());

    //Adding a ticket
    $('#addTicket').click(function (event) {
        event.preventDefault();
        add_ticket();
    });




    $('#confirm-button')[0].addEventListener('click', function (event) {
        event.preventDefault();
        var add_tickets = [];
        var update_tickets = [];
        var delete_tickets = [];

        // console.log($("#setRegistration").valid());
        if ($("#setRegistration").valid()) {
            var currency_flag = true;
            var positive_flag = true;
            $.each($('.ticket_group'), function (index, ticket) {
                var currency_list = [];
                $(ticket).find('.currency').each(function (index, element) {
                    currency_list.push($(element).val())
                });
                // console.log(index, currency_list);

                if (checkDuplicateInArray(currency_list)) currency_flag = false;
                $(ticket).find('input[name=price]').each(function (index, element) {
                    if (isNaN($(element).val()) || Number($(element).val()) <= 0) {
                        positive_flag = false;
                    }
                });
            });
            if (currency_flag && positive_flag) {
                $('.add-ticket').each(function () {
                    // console.log($(this));
                    add_tickets.push({
                        'name': $(this).find('.ticket-title').val(),
                        'start_date': $(this).find('input[name=\'start\']').val(),
                        'end_date': $(this).find('input[name=\'end\']').val(),
                        'ticket_div_id': $(this).attr('id'),
                        'price': get_price(this)
                    });
                });
                $('.change-ticket').each(function () {
                    update_tickets.push({
                        'ticket_id': $(this).find('.ticket-title').data('ticket-id'),
                        'ticket_title': $(this).find('.ticket-title').val(),
                        'ticket_price': get_price(this),
                        'start_date': $(this).find('input[name=\'start\']').val(),
                        'end_date': $(this).find('input[name=\'end\']').val()
                    });
                });
                $('.remove-ticket').each(function () {
                    delete_tickets.push($(this).find('.ticket-title').data('ticket-id'));
                });
                if (add_tickets.length === 0 && update_tickets.length === 0 && delete_tickets.length === 0) {
                    swal({
                        title: "Success!",
                        type: "success",
                        text: "Your information has been saved.",
                        timer: 2000,
                        showConfirmButton: false
                    });
                }
            } else if (!currency_flag) {
                swal({
                    title: "Warning",
                    type: "warning",
                    text: "Each currency can only be selected once. Please check.",
                    showConfirmButton: true
                });
            } else if (!positive_flag) {
                swal({
                    title: "Warning",
                    type: "warning",
                    text: "Price should be positive number. Please check.",
                    showConfirmButton: true
                });
            }
        }

        if (add_tickets.length) {
            var add_ticket_json = {
                conference_id: conferenceID,
                add_tickets: add_tickets,
            };

            $.ajax({
                type: "POST",
                url: endpoints["addTickets"],
                contentType: "application/json",
                data: JSON.stringify(add_ticket_json),
                success: function (response) {
                    swal({
                        title: "Success!",
                        type: "success",
                        text: "Your information has been saved.",
                        timer: 2000,
                        showConfirmButton: false
                    });
                    for (var prop in response) {
                        // console.log(prop);
                        $('.add-ticket').each(function () {
                            // console.log(prop);
                            // console.log($(this).attr('id'));
                            if ($(this).attr('id') === prop) {
                                // console.log(response[prop]);
                                $(this).find('.unconceal').attr('disabled', false);
                                $(this).find('.ticket-title').attr('data-ticket-id', response[prop]);
                                $(this).find('.ticket-price').attr('data-ticket-id', response[prop]);
                                $(this).find('.status').attr('data-ticket-id', response[prop]);
                                $(this).find('.remove').attr('data-ticket-id', response[prop]);
                                $(this).toggleClass('origin-ticket add-ticket');

                            }
                        });
                    }
                }
            })
            .fail(function (data, textStatus, error) {
                if (data.status === 406) {
                    swal({
                        title: "Oops...",
                        type: "error",
                        text: "Please provide date.",
                        confirmButtonText: "Got it!"
                    });
                }
            });
        }

        if (update_tickets.length) {
            // console.log(update_tickets);
            var update_ticket_json = {
                conference_id: conferenceID,
                update_tickets: update_tickets
            };

            $.ajax({
                type: "PUT",
                url: endpoints["updateTickets"],
                contentType: "application/json",
                data: JSON.stringify(update_ticket_json),
                success: function (response) {
                    swal({
                        title: "Success!",
                        type: "success",
                        text: "Your information has been saved.",
                        timer: 2000,
                        showConfirmButton: false
                    });
                    for (var prop in response) {
                        // console.log(prop);
                        $('.change-ticket').each(function () {
                            $(this).toggleClass('change-ticket');
                        });
                    }
                }
            })
            .fail(function (data, textStatus, error) {
                if (data.status === 406) {
                    swal({
                        title: "Oops...",
                        type: "error",
                        text: "Please provide date.",
                        confirmButtonText: "Got it!"
                    });
                }
            });
        }

        if (delete_tickets.length) {
            // console.log(update_tickets);
            var delete_ticket_json = {
                conference_id: conferenceID,
                delete_tickets: delete_tickets,
            };

            $.ajax({
                type: "DELETE",
                url: endpoints["deleteTickets"],
                contentType: "application/json",
                data: JSON.stringify(delete_ticket_json),
                success: function (response) {
                    swal({
                        title: "Success!",
                        type: "success",
                        text: "Your information has been saved.",
                        timer: 2000,
                        showConfirmButton: false
                    });
                }
            })
            .fail(function (data, textStatus, error) {
                console.log(error);
            });
        }
    });


    /********* promo code construction ***********/
    // cannot integrate with ticket validate
    $('#modal-form').validate({
        errorPlacement: function (error, element) {
            if (element.parent().hasClass('input-daterange')) {
                error.appendTo(element.parent().parent());
            } else {
                error.appendTo(element.parent());
            }
        }
    });

    jQuery.validator.addMethod("positive_number", function (value, el, param) {
        return value >= 0;
    }, "The input value must be positive");

    jQuery.validator.classRuleSettings.positive_number = {positive_number: true, required: true};

    $('#promoCodeForm').on('show.bs.modal', function (event) {
        var action = $(event.relatedTarget).attr('data-action');
        // datepicker can also fire this function. this can avoid that
        if (typeof action === "undefined") {
            return;
        }
        var modal = $(this);
        var ajax_method = "";
        // clean the form
        modal.find('#modal-form')[0].reset();
        if (action === "new_promo_code") {
            ajax_method = "POST";
            // set initial date
            $("#promo-value").attr("disabled", false);
            $("#promo-type").attr("disabled", false);
            $("#promo-currency").attr("disabled", false);
            modal.find("#promo-start").attr('value', get_today());
            modal.find("#promo-start").datepicker('update', get_today());
            modal.find("#promo-end").datepicker('update', "");
            modal.find(".input-daterange").datepicker('updateDates');
        } else if (action === "promo_code_edit") {
            ajax_method = "PUT";
            var promo_code_tr = $(event.relatedTarget).parent().parent();
            // update input in the modal
            modal.find("#promo_code_id").val($(event.relatedTarget).attr('data-promo-code-id'));
            modal.find("#promo-code").val(promo_code_tr.find('.promo-code').html());
            // console.log(promo_code_tr.find('.promo-type').val());
            modal.find("#promo-type").val(promo_code_tr.find('.promo-type').val());
            $("#promo-type").attr("disabled", true);
            modal.find("#promo-currency").val(promo_code_tr.find('.project-title small:eq(1)').data('promo-code-currency'));
            $("#promo-currency").attr("disabled", true);
            modal.find("#promo-value").val(promo_code_tr.find('.project-title small:eq(0)').data('promo-code-value'));
            $("#promo-value").attr("disabled", true);
            if (promo_code_tr.find('.project-completion > small').attr('data-promo-code-quantity') === '-1') {
                modal.find("#usage_limit_type_no_limit").prop("checked", true);
                modal.find("input[name=quantity]").prop("disabled", true);
                modal.find("input[name=quantity]").prop("required", false);
                modal.find("#quantity-error").hide();
            } else {
                modal.find("#usage_limit_type_with_limit").prop("checked", true);
                modal.find("input[name=quantity]").prop("disabled", false);
                modal.find("input[name=quantity]").prop("required", true);
                modal.find("input[name=quantity]").val(promo_code_tr.find('.project-completion > small').attr('data-promo-code-quantity'));
                modal.find("#usage_limit_type_with_limit").val(promo_code_tr.find('.project-completion > small').attr('data-promo-code-quantity'));
            }
            // update date range
            modal.find("#promo-start").attr('value', promo_code_tr.find('.project-people > div').attr('data-promo-code-start-date'));
            modal.find("#promo-end").attr('value', promo_code_tr.find('.project-people > div').attr('data-promo-code-end-date'));
            // update function cause the disapperance of date which is before today
            // modal.find("#promo-start").datepicker('update', promo_code_tr.find('.project-people > div').attr('data-promo-code-start-date'));
            // modal.find("#promo-end").datepicker('update', promo_code_tr.find('.project-people > div').attr('data-promo-code-end-date'));
            modal.find(".input-daterange").datepicker('updateDates');
        }

        // ajax put or post
        $("#save-new-promo-code").click(function (save_event) {
            save_event.preventDefault();
            if ($("#modal-form").valid()) {
                // get promo code info
                // console.log($("input[name=usage_limit_type]:checked"));
                var promo_code_json = {
                    "promo_code": document.getElementById("promo-code").value,
                    "promo_type": document.getElementById("promo-type").value,
                    "promo_value": document.getElementById("promo-value").value,
                    "promo_currency": document.getElementById("promo-currency").value,
                    "promo_limit": $("input[name=usage_limit_type]:checked").val(),
                    "promo_start": $("#promo-start").val(),
                    "promo_end": $("#promo-end").val()
                };
                // console.log(promo_code_json);
                var json_pack = {};
                var url = "";
                if (action === "new_promo_code") {
                    json_pack = promo_code_json;
                    url = endpoints["addPromoCode"];
                } else if (action === "promo_code_edit") {
                    json_pack = {
                        "action": "edit",
                        "promo_code": promo_code_json,
                        "promo_code_id": modal.find("#promo_code_id").attr('value')
                    };
                    url = endpoints['updatePromoCode'];
                }

                $.ajax({
                    type: ajax_method,
                    url: url,
                    contentType: "application/json",
                    data: JSON.stringify(json_pack),
                    success: function (response) {
                        swal({
                            title: "Success!",
                            type: "success",
                            text: "Your promo code has been saved.",
                            timer: 2000,
                            showConfirmButton: false
                        });
                        if (action === "new_promo_code") {
                            render_new_promo_code(response);
                        } else if (action === "promo_code_edit") {
                            update_promo_code_info(response, promo_code_tr);
                        }
                    }
                })
                .fail(function (data, textStatus, error) {
                    swal({
                        title: "Oops...",
                        type: "error",
                        text: data.responseJSON.message,
                        confirmButtonText: "Got it!"
                    });
                });
                modal.modal('hide');
            }
        });
    }).on('hide.bs.modal', function (event) {
        // IMPORTANT!!!! unbind the click. If don't unbind click will fire multiple times
        $(this).find('#modal-form')[0].reset();
        if (event.namespace === "bs.modal") {
            $("#save-new-promo-code").unbind();
        }
    });


    // add delegate to count existing tickets whose title or price have been changed
    $('.project-list').delegate('.promo-status', 'click', function (event) {
        event.preventDefault();
        var button = $(this);
        button.attr('disabled', true);
        $.ajax({
            type: "PUT",
            url: endpoints["updatePromoCode"],
            contentType: "application/json",
            data: JSON.stringify({
                "action": button.attr('data-action'),
                "promo_code_id": button.attr('data-promo-code-id')
            }),
            success: function (response) {
                // swal({title: "Success!", type: "success", text: "Your promo code has been saved.", timer: 2000, showConfirmButton: false});
                update_promo_code_info(response, button.parent().parent());
                button.attr('disabled', false);
            }
        })
        .fail(function (data, textStatus, error) {
            swal({
                title: "Oops...",
                type: "error",
                text: "Something is wrong, try again later or contact with customer service",
                confirmButtonText: "Got it!"
            });
            button.attr('disabled', false);
        });
    });
});
