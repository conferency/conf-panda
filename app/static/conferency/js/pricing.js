var dollar = 200;
var tickets = 50;
UpdateTable = function () {
    if ((dollar != 200) || (tickets != 50)) {
        tickets_dragger.enable();
        price_dragger.enable();
    }
    var conferency_service_fee_rate = 0;
    var conferency_service_fee_surplus = 1;
    var conferency_credit_card_fee_rate = 0.03;

    var eventbrite_service_fee_rate = 0.025;
    var eventbrite_service_fee_surplus = 0.99;
    var eventbrite_credit_card_fee_rate = 0.03;

    var ticketleap_service_fee_rate = 0.02;
    var ticketleap_service_fee_surplus = 1;
    var ticketleap_credit_card_fee_rate = 0.03;

    var regonline_service_fee_rate = 0;
    var regonline_service_fee_surplus = 3.95;
    var regonline_credit_card_fee_rate = 0.0495;

    if (dollar == 0) {
        $('#free-event').show();
        $('#non-free-table').show();

        $('#non-free-inf').hide();
        conferency_service_fee_surplus = 0;
        eventbrite_service_fee_rate = 0;
        ticketleap_service_fee_rate = 0;
        eventbrite_service_fee_surplus = 0;
        ticketleap_service_fee_surplus = 0;

    } else if (dollar == -1) {
        $('#free-event').hide();
        $('#non-free-table').hide();
        $('#non-free-inf').show();
        tickets_dragger.disable();
    } else {
        $('#free-event').hide();
        $('#non-free-table').show();
        $('#non-free-inf').hide();
    }
    var eventbrite_fee = (((eventbrite_service_fee_rate + eventbrite_credit_card_fee_rate) * 100000 * dollar) / 100000 + eventbrite_service_fee_surplus).toFixed(2);
    var ticketleap_fee = (((ticketleap_service_fee_rate + ticketleap_credit_card_fee_rate) * 100000 * dollar) / 100000 + ticketleap_service_fee_surplus).toFixed(2);
    var regonline_fee = (((regonline_service_fee_rate + regonline_credit_card_fee_rate) * 100000 * dollar) / 100000 + regonline_service_fee_surplus).toFixed(2);
    var conferency_fee = (((conferency_service_fee_rate + conferency_credit_card_fee_rate) * 100000 * dollar) / 100000 + conferency_service_fee_surplus).toFixed(2);


    $('#holder-get').text("$" + (dollar * tickets).toFixed(2));
    $('#buyer-price').text("$" + conferency_fee);
    $('#total-cost').text("$" + (tickets * conferency_fee).toFixed(2));

    if (eventbrite_fee - eventbrite_credit_card_fee_rate * dollar > 9.95) eventbrite_fee = 9.95 + eventbrite_credit_card_fee_rate * dollar;
    if (ticketleap_fee - ticketleap_credit_card_fee_rate * dollar > 10) ticketleap_fee = 10 + ticketleap_credit_card_fee_rate * dollar;

    if (0 < dollar && dollar < 5) {
        ticketleap_fee = 0.25;
    }

    $('#saving-eventbrite').text("$" + (tickets * (eventbrite_fee - conferency_fee)).toFixed(2));
    $('#saving-ticketleap').text("$" + (tickets * (ticketleap_fee - conferency_fee)).toFixed(2));
    $('#saving-regonline').text("$" + (tickets * (regonline_fee - conferency_fee)).toFixed(2));


    if (tickets == -1 && dollar != 0) {
        $('#free-event').hide();
        $('#non-free-table').hide();
        $('#non-free-inf').show();
        price_dragger.disable();
    }

};

var price_dragger = new Dragdealer('price-slider', {
    animationCallback: function (x, y) {
        if (tickets != -1) {
            dollar = Math.round(x * 1000);
            dollar = dollar == 1000 ? -1 : dollar;
            $('#price-value').text(dollar == -1 ? "$1000+" : "$" + dollar);
            UpdateTable()
        } else {
            price_dragger.value = dollar / 1000
        }
    }, x: 0.2
});
var tickets_dragger = new Dragdealer('tickets-slider', {
    animationCallback: function (x, y) {
        if (dollar != -1) {
            tickets = Math.round(x * 1000);
            tickets = tickets == 1000 ? -1 : tickets;
            $('#tickets-value').text(tickets == -1 ? "1000+" : tickets);
            UpdateTable()
        }
    }, x: 0.05
});

$('#span-eventbrite').tooltip({
    container: 'body',
    html: true,
    title: "Eventbrite Serivce Fee: 2.5% + $0.99, capped at $9.95 per ticket<br>Credit Card Fee: 3%"
});

$('#span-ticketleap').tooltip({
    container: 'body',
    html: true,
    title: "Ticketleap Serivce Fee: $1 + 2%, capped at $10 per ticket<br>Credit Card Fee: 3%" +
    "<br>$0.25 per ticket if ticket price $5 or less"
});

$('#span-regonline').tooltip({
    container: 'body',
    html: true,
    title: "RegOnline Serivce Fee: $3.95 per ticket<br>Credit Card Fee: 4.95%"
});