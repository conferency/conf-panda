/**
 * No Logic should go in this file, please insert logic to another file
 * and load scripts here
 */
(function(window, document) {"use strict";

var jQuery, $; // Localize jQuery variables

function loadScript(url, callback) {
    /* Load script from url and calls callback once it's loaded */
    var scriptTag = document.createElement('script');
    scriptTag.setAttribute("type", "text/javascript");
    scriptTag.setAttribute("src", url);
    if (typeof callback !== "undefined") {
        if (scriptTag.readyState) {
            /* For old versions of IE */
            scriptTag.onreadystatechange = function () {
            if (this.readyState === 'complete' || this.readyState === 'loaded') {
                callback();
            }
          };
        } else {
            scriptTag.onload = callback;
        }
    }
    (document.getElementsByTagName("head")[0] || document.documentElement).appendChild(scriptTag);
}

/* Load jQuery */
loadScript("https://code.jquery.com/jquery-2.2.4.min.js", function() {
  /* Restore $ and window.jQuery to their previous values and store the
     new jQuery in our local jQuery variables. */
  $ = jQuery = window.jQuery.noConflict(true);
  /* Load jQuery plugin and execute the main logic of our widget once the
     plugin is loaded is loaded */

    var getScriptParameter = function(url, sParam) {
        var sPageURL = url;
        var params = url.split('?');
        if (params.length < 2) {
            return "";
        }
        var paramStr = params[1];
        var sURLVariables = paramStr.split('&');
        for (var i = 0; i < sURLVariables.length; i++) {
            var sParameterName = sURLVariables[i].split('=');
            if (sParameterName[0] == sParam) {
                return sParameterName[1];
            }
        }
    }

    // Get event_id
    var scriptSrc = document.getElementById("embeded-conferency-script").src.toLowerCase();
    var cid = getScriptParameter(scriptSrc, "cid");
    var op = getScriptParameter(scriptSrc, "op");
    var host = getScriptParameter(scriptSrc, "host");
    console.log("loading " + cid);
    console.log("loading " + op);
    console.log("loading " + host);

    /* REPLACE "/static/embed/js/agendawidget.js" WITH JS FILE HOSTED ON WHOVA */
    loadScript(host + "/static/conferency/js/embedloader.js?cid=" + cid + "&op=" + op + "&host=" + host + "&update=" + Math.floor(Date.now() / 1000), function() {
        initAddWidgetPlugin(jQuery);
    });
});

}(window, document));
