var saved = true;
function save_detect(elems) {
    for(var i = 0; i < elems.length; i++) {
        // console.log(elems[i]);
        if(elems[i].includes("i-checks")) {
            // console.log(elems[i]);
            $(elems[i]).on("ifChanged", function(e) {
                saved = false;
            });
        } else if (elems[i] == ".edit-button") {
            // console.log($(elems[i]));
            $(elems[i]).on("click", function (e) {
                saved = false;
            });
        } else {
            $(elems[i]).on("change", function (e) {
                // console.log('change');
                saved = false;
            });
        }
    }
}

window.onbeforeunload = function(e) {
    // console.log(e);
    if (!saved) {
        var dialogText = "There are unsaved changes!";
        e.returnValue = dialogText;
        return dialogText;
    }
};
