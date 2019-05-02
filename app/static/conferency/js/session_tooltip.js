function generate_tooltip(event, allow_edit) {
    if (allow_edit === undefined) {
        fruit = false;
    }
            var tooltip = '<div class="tooltiptopicevent">' + '<h3>' + event.title + '</h3>';
            if (event.type === "regular") {
                var type = "Regular Session";
            } else if (event.type === "keynote") {
                var type = "Keynote/Panel"
            }  else if (event.type === "workshop") {
                var type = "Workshop";
            } else {
                var type = "Paper Session";
            }
            tooltip = tooltip + '<ul class="unstyled"><li>Start: ' + event.start_time + '</li><li>End: ' + event.end_time +
                '</li><li>Venue: ' + event.venue + '</li><li>Type: ' + type + '</li>';
            if (event.type !== "regular") {
                if (event.type !== "paper") {
                    if (event.speakers.length) {
                        tooltip = tooltip + '<li>Speakers: <ul>';
                        for (var i = 0; i < event.speakers.length; i++) {
                            tooltip = tooltip + '<li>' + event.speakers[i].first_name + " " + event.speakers[i].last_name + " (" + event.speakers[i].organization + ")</li>";
                        }
                        tooltip = tooltip + '</ul></li>';
                    }
                }
                if (event.moderators.length) {
                    tooltip = tooltip + '<li>Moderators: <ul>';
                    for (var i = 0; i < event.moderators.length; i++) {
                        tooltip = tooltip + '<li>' + event.moderators[i].first_name + " " + event.moderators[i].last_name + " (" + event.moderators[i].organization + ")</li>";
                    }
                    tooltip = tooltip + '</ul></li>';
                }
                if (event.type === "paper") {
                    tooltip = tooltip + '<li>Papers: <ul>';
                    for (var i = 0; i < event.papers.length; i++) {
                        var label = event.papers[i].label ? (" (" + event.papers[i].label + ") ") : " ";
                        tooltip = tooltip + '<li>' + event.papers[i].title + label + '<ul class="unstyled">';
                        if (event.papers[i].authors.length) {
                            tooltip = tooltip + '<li>Authors: <ul>';
                            for (var j = 0; j < event.papers[i].authors.length; j++) {
                                tooltip = tooltip + '<li>' + event.papers[i].authors[j].first_name + " " + event.papers[i].authors[j].last_name + " (" + event.papers[i].authors[j].organization + ")</li>";
                            }
                            tooltip = tooltip + "</ul></li>";
                        }
                        if (event.papers[i].discussants.length) {
                            tooltip = tooltip + '<li>Discussants: <ul>';
                            for (var j = 0; j < event.papers[i].discussants.length; j++) {
                                tooltip = tooltip + '<li>' + event.papers[i].discussants[j].first_name + " " + event.papers[i].discussants[j].last_name + " (" + event.papers[i].discussants[j].organization + ")</li>";
                            }
                            tooltip = tooltip + "</ul></li>";
                        }
                        tooltip = tooltip + '</ul></li>';
                    }
                    tooltip = tooltip + '</ul></li>';
                }
            }
            if (event.description) {
				tooltip = tooltip + '<li>Description: ' + event.description + '</li>';
			}

            if (allow_edit) {
                return tooltip + '</ul><p class="text-warning">Click to session to edit</p></div>';
            } else {
                 return tooltip + '</ul></div>';
            }
            
        }