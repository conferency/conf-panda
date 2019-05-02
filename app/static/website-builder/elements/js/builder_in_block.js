(function () {

	//remove portfolio overlays

	var overlays = document.querySelectorAll('a > .overlay');

	for ( var i = 0; i < overlays.length; i++ ) overlays[i].remove();

} ());