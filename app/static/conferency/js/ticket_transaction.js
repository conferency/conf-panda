// for free registration
var need_payment = true;
// stripe
Stripe.setPublishableKey(publishable_key);
var stripe = Stripe(publishable_key);

function stripeResponseHandler(status, response) {
    if(status == 200) {
        // $("input[name=stripe_token]").val(response.id);
        $('#stripeToken').val(response.id)
        // $("#submit_button").removeAttr('disabled');
        // console.log('before');
        $('#RegistrationForm').off("submit");
        // console.log('middle');
        $("#RegistrationForm").submit();
        // console.log('after');
    } else {
        // console.log(response.error.type);
        // console.log(response.error.code);
        // console.log(response.error.message);
        // console.log(response.error.param);
        swal({
            title: "Sorry, we could not complete your purchase",
            type: "warning",
            text: response.error.message,
            confirmButtonText: "Got it!",
            confirmButtonColor: "#1AB394"});
        $("#submit_button").removeAttr('disabled');
    }
}

function disable_payment_info(value) {
    // disable the input and select in the payment-info
    if (value) {
        $('#payment-info input, #payment-info select').prop('disabled', true);
    } else {
        $('#payment-info input, #payment-info select').prop('disabled', false);
    }
}

function update_product_select(element) {
    // update the value of corresponding checkbox
    var corresponding_checkbox = document.getElementById(element.parentNode.getElementsByTagName('label')[0].getAttribute('for'));
    corresponding_checkbox.value = element.value;
    if (corresponding_checkbox.checked) {
        get_price();
    }
}

function floatToString(num) {
    if (num.toString().indexOf('.') === -1) {
        return num.toFixed(1);
    } else {
        return num;
    }
}

function get_price() {
    // console.log(get_ticket_price());
    var total = 0;
    // get ticket id
    var price_id = $('#RegistrationForm').find('input[name="tickets"]:checked').val();
    var product_options = "option_ids=";
    // product query
    $('#RegistrationForm').find('input[name="products"]:checked').each(function() {
        product_options+=($(this).val() + ',');
    });

    if(typeof price_id === 'undefined') {
        // regisration is not open yet
        return;
    } else {
        $.when(
            $.getJSON('/api/ticket_prices/' + price_id),
            $.ajax({
                type : "GET",
                url: get_product_options_url,
                data: product_options
            }),
            $.getJSON(get_promo_code_url + $('#promo_code_info').find('code').data('promo-code-id'))
        )
            .done(function(result_1, result_2, result_3) {
                // add ticket price
                total += parseFloat(result_1[0].amount);
                // console.log(result_2);
                // console.log(result_1[0]);
                // add product price
                if (result_2[1] === 'success') {
                    for (var i = 0; i < result_2[0].product_options_info.length; i++) {
                        // console.log(result_2[0].product_options_info[i].currency, result_1[0].currency);
                        if (result_2[0].product_options_info[i].currency === result_1[0].currency) {
                            total += parseFloat(result_2[0].product_options_info[i].option_price);
                        }
                    }
                }
                // calculate discount
                if (result_3[1] === 'success' && (result_1[0].currency === result_3[0].currency)) {
                    if (result_3[0].type === 'percentage') {
                        total *= (1-parseFloat(result_3[0].value)/100);
                    } else {
                        total -= parseFloat(result_3[0].value);
                    }
                }
                // if (result_3[0] && (result_1[0].currency === result_3[0].currency)) {
                    // $("#promo-code").prop("disabled", false);
                    // $(".product_select").prop("disabled", false);
                    // $("#check_promo_code").prop("disabled", false);
                    // $(".product-select").iCheck("enable");
                // } else {
                    // disable product and promocode
                    // $("#promo-code").prop("disabled", true);
                    // $(".product_select").prop("disabled", true);
                    // $("#check_promo_code").prop("disabled", true);
                    // $(".product-select").iCheck("disable");
                // }
                if (total <= 0) {
                    $('#total-price').text('Free');
                    disable_payment_info(true);
                    need_payment = false;
                } else {
                    $('#total-price').text(floatToString(total) + " " + result_1[0].currency);
                    disable_payment_info(false);
                    need_payment = true;
                }
                $('#total-price').attr('data-price', total);
            })
                .fail(function(response) {
                    swal({title: "Oops...", type: "error", text: response.responseJSON.message, confirmButtonText: "Got it!"});
                });
    }
    // get promo
    // var promo_code_id = $('#promo_code_info').find('code').data('promo-code-id');
    // console.log(total);
}

$(document).ready(function () {
    // get initial price
    get_price();

    $("#RegistrationForm").submit(function(event) {
        if (need_payment) {
            if ($("#RegistrationForm").valid()) {
                // disable the submit button to prevent repeated clicks
                $('#submit_button').prop("disabled", true);
                // var amount = $("input[name=tickets]:checked").val();
                Stripe.card.createToken({
                    number: $('#card_number').val(),
                    cvc: $('#security_code').val(),
                    exp_month: $('#month').val(),
                    exp_year: $('#year').val(),
                    name: $('#holder_name').val()
                }, stripeResponseHandler);
                // prevent the form from submitting with the default action
               return false;
            }
        } else {
        }
    });

    // get selected price
    $('.ticket-select, .product-select').on('ifChecked ifUnchecked', function(event){
        // ignore ifUnchecked of radio
        if (event.type === 'ifUnchecked' && event.target.classList.contains('ticket-select')) {
            return;
        } else {
            get_price();
        }
    });

    // check promo code
    $('#check_promo_code').click(function(event){
        event.preventDefault();
        if (!!$('#promo-code').val()) {
            var check_promo_code_with_id = check_promo_code_url + $('#promo-code').val();
            $.getJSON(check_promo_code_with_id, function(data) {
                event.target.parentNode.parentNode.classList.remove("has-error");
                $('#promo_code_error').text('');
                if (data.type === 'fixed_amount') {
                    $('#promo_code_info').empty().append('<code data-promo-code-id="'+data.id+'">'+data.promo_code+': '+data.value+' off (only works on ' + data.currency + ')</code>');
                } else {
                    $('#promo_code_info').empty().append('<code data-promo-code-id="'+data.id+'">'+data.promo_code+': '+data.value+'% off (only works on ' + data.currency + ')</code>');
                }
                $('#promo_code').val(data.id);
                get_price();
            })
                .fail(function(response) {
                    event.target.parentNode.parentNode.classList.remove("has-error");
                    event.target.parentNode.parentNode.classList.add("has-error");
                    // console.log(response);
                    $('#promo_code_error').text(response.responseJSON.message);
                    $('#promo_code_info').empty();
                    get_price();
                    $('#promo_code').val('');
                    // console.log(response.responseText);
                });
        } else {
            event.target.parentNode.parentNode.classList.remove("has-error");
            event.target.parentNode.parentNode.classList.add("has-error");
            $('#promo_code_error').text('Please enter the promo code');
            $('#promo_code_info').empty();
            $('#promo_code').val('');
            get_price();
        }
    });
});
