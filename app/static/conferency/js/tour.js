var initializeTour = function (tourFinishedUrl) {
    function mark_tour_hide() {
        $.ajax({
            type: "POST",
            url: tourFinishedUrl,
            contentType: "application/json",
            data: JSON.stringify({timestamp: Date(), status: true})
        });
        tour.cancel();
    }

    function fix_height() {
        var h = $("#tray").height();
        $("#preview").attr("height", (($(window).height()) - h) + "px");
    }

    $(window).resize(function () {
        fix_height();
    }).resize();

    $('.sidebar-collapse').slimScroll({
        height: '100%',
        railOpacity: 0.9
    });

    tour = new Shepherd.Tour({
        defaults: {
            classes: 'shepherd-theme-arrows',
            scrollTo: true
        }
    });

    tour.addStep('conference_switch', {
        text: 'Use this menu to switch to any conference site.',
        attachTo: '#conferences_selector bottom',
        showCancelLink: true,
        buttons: [{
            text: 'Next',
            action: tour.next
        }, {
            text: 'Skip',
            action: tour.cancel,
            classes: 'shepherd-button-exit'
        }, {
            text: 'Hide on next login',
            action: mark_tour_hide,
            classes: 'shepherd-button-hide'
        }]
    });

    tour.addStep('sidebar', {
        text: 'Based on your roles in different conferences, this navigation menu may change.<br> ' +
        'For example, if you are the chair of a conference, you should see the Administration menu here.',
        attachTo: '.navbar-static-side right',
        showCancelLink: true,
        buttons: [{
            text: 'Previous',
            action: tour.back,
            classes: 'shepherd-button-previous'
        }, {
            text: 'Next',
            action: tour.next
        }, {
            text: 'Skip',
            action: tour.cancel,
            classes: 'shepherd-button-exit'
        }, {
            text: 'Hide on next login',
            action: mark_tour_hide,
            classes: 'shepherd-button-hide'
        }]
    });

    tour.addStep('mini', {
        text: 'You can get more space by hiding the navigation menu.',
        attachTo: '.navbar-minimalize bottom',
        showCancelLink: true,
        buttons: [{
            text: 'Previous',
            action: tour.back,
            classes: 'shepherd-button-previous'
        }, {
            text: 'Next',
            action: tour.next
        }, {
            text: 'Skip',
            action: tour.cancel,
            classes: 'shepherd-button-exit'
        }, {
            text: 'Hide on next login',
            action: mark_tour_hide,
            classes: 'shepherd-button-hide'
        }]
    });

    tour.addStep('contact', {
        text: 'You can get help by contacting us here.',
        attachTo: '#launcher top',
        showCancelLink: true,
        classes: 'hotfix-arrow-contact shepherd-step shepherd-theme-arrows ' +
        'shepherd-has-cancel-link shepherd-element shepherd-element-attached-bottom ' +
        'shepherd-element-attached-center shepherd-target-attached-top shepherd-target-attached-center',
        buttons: [{
            text: 'Previous',
            action: tour.back,
            classes: 'shepherd-button-previous'
        }, {
            text: 'Next',
            action: tour.next
        }, {
            text: 'Skip',
            action: tour.cancel,
            classes: 'shepherd-button-exit'
        }, {
            text: 'Hide on next login',
            action: mark_tour_hide,
            classes: 'shepherd-button-hide'
        }]
    });

    tour.addStep('guide', {
        text: 'You can come back to the tour here.',
        attachTo: '#guide_button bottom',
        showCancelLink: true,
        classes: 'hotfix-arrow-right-top shepherd-theme-arrows' +
        ' shepherd-has-cancel-link shepherd-element shepherd-element-attached-top' +
        ' shepherd-element-attached-center shepherd-target-attached-bottom shepherd-target-attached-center',
        buttons: [{
            text: 'Previous',
            action: tour.back,
            classes: 'shepherd-button-previous'
        }, {
            text: 'Hide on next login',
            action: mark_tour_hide,
            classes: 'shepherd-button-hide'
        }]
    });

    tour.on('complete', function () {
        // console.log("tour finished");
        sessionStorage.setItem('tour', false);
    });

    tour.on('cancel', function () {
        // console.log("tour cancelled");
        sessionStorage.setItem('tour', false);
    });

    return tour;
};
