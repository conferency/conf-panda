function initAddWidgetPlugin(jQuery) {
    (function ( $ ) {
        $.fn.addWidget = function() {
            // Get event_id
            var scriptSrc = document.getElementById("embeded-conferency-script").src.toLowerCase();

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

            var cid = getScriptParameter(scriptSrc, "cid");
            var op = getScriptParameter(scriptSrc, "op");
            var host = getScriptParameter(scriptSrc, "host");
            var url = host + "/conference/" + cid + "/"+ op;
            var iframe_src = '<iframe title="" name="conferency-embed-frame" style="border:0;" src="' + url + '"' + ' width="100%" frameBorder="0" scrolling="no"></iframe>';
            var style_src = '<style>.brandlink{color:#000}.brandlink:hover{color:#2dacee}</style>';

            /* REPLACE "(HOST)/embeded/" WITH AGENDA LINK GENERATED FROM USER */
            this.html(iframe_src+style_src);

            //Adjust code styling
            function adjust_style() {
                $("#conferency-embed").parent().css({'min-height': '750px', 'width': '100%', 'height': 'auto', 'max-width': '768px', 'margin': '0 auto'})
                $("#conferency-embed").css({"padding": "5px 0px"})
                // $("#whova-wrap").css({"display":"block", "margin-top": "10px", "text-align":"right", "font-weight":"200", "padding-right":"45px"});
                // $('.brandwrap').show();
                // $('#whova-wrap').show();
                // $("#whova-emslink").css({"font-size":"10px", "color":"gray"});
            }

            function whovaListenIframeMessage (host) {
                window.addEventListener('message', function(evt){
                    if(evt.origin.indexOf(host) <= -1) return;
                    var data = {};
                    try {
                        data = JSON.parse(evt.data);
                    } catch (e) {}
                    if(data.embed_height) {
                        $('#conferency-embed iframe').height(data.embed_height);
                    } else if(data.agenda_widget_scrollpos){
                        $(window).scrollTop(parseFloat(data.embed_height));
                    }
                }, false);
            }

            function emitScrollPos(host){
                var $frame;
                if($('#conferency-embed iframe').length){
                    $frame = $('#conferency-embed iframe');
                }
                if($('#conferency-embed iframe').length){
                    $frame = $('#conferency-embed iframe');
                }
                var iframe = $frame[0].contentWindow;
                iframe.postMessage(JSON.stringify({agendaWidgetScrollTop: 0, parentWidgetScrollPos: $(window).scrollTop()}), host);
                setInterval(function(){
                    iframe.postMessage(JSON.stringify({agendaWidgetScrollTop: $frame.offset().top, parentWidgetScrollPos: $(window).scrollTop()}), host);
                }, 500);
            }
            whovaListenIframeMessage(host);
            emitScrollPos(host);
            adjust_style();
            return this;
        };
    }( jQuery ));
    jQuery(document).ready(function($) {
        if ($("#conferency-embed").length > 0) {
            $("#conferency-embed").addWidget();
        }
    });
}
