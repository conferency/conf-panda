var title_paper = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*TITLE*',
        tooltip: 'Title of the paper',
        click: function () {

            context.invoke('editor.insertText', '*TITLE*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var title_submission = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*TITLE*',
        tooltip: 'Title of the submission',
        click: function () {

            context.invoke('editor.insertText', '*TITLE*');
        }
    });
    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");

    return render;   // return button as jquery object
};

var name_recipient = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*NAME*',
        tooltip: 'Name of the recipient',
        click: function () {

            context.invoke('editor.insertText', '*NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var name_author = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*NAME*',
        tooltip: 'Name of the author',
        click: function () {

            context.invoke('editor.insertText', '*NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var status_submission = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*STATUS*',
        tooltip: 'Submission status',
        click: function () {

            context.invoke('editor.insertText', '*STATUS*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var first_name_recipient = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*FIRST_NAME*',
        tooltip: 'Recipient\'s first name',
        click: function () {

            context.invoke('editor.insertText', '*FIRST_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var last_name_recipient = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*LAST_NAME*',
        tooltip: 'Recipient\'s last name',
        click: function () {

            context.invoke('editor.insertText', '*LAST_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var first_name_author = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*FIRST_NAME*',
        tooltip: 'Author\'s first name',
        click: function () {

            context.invoke('editor.insertText', '*FIRST_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var last_name_author = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*LAST_NAME*',
        tooltip: 'Author\'s last name',
        click: function () {

            context.invoke('editor.insertText', '*LAST_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var contact_email = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*CONTACT_EMAIL*',
        tooltip: 'Contact email address of the conference',
        click: function () {

            context.invoke('editor.insertText', '*CONTACT_EMAIL*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var track_name = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*TRACK_NAME*',
        tooltip: 'Name of the selected track',
        click: function () {

            context.invoke('editor.insertText', '*TRACK_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var conference_name = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*CONFERENCE_NAME*',
        tooltip: 'Name of the conference',
        click: function () {

            context.invoke('editor.insertText', '*CONFERENCE_NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var conference_website = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*CONFERENCE_WEBSITE*',
        tooltip: 'Website of the conference',
        click: function () {

            context.invoke('editor.insertText', '*CONFERENCE_WEBSITE*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var paper_review_system = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*PAPER_REVIEW_SYSTEM*',
        tooltip: 'Url of the system',
        click: function () {
            context.invoke('editor.insertText', '*PAPER_REVIEW_SYSTEM*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var review_assignment = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*REVIEW_ASSIGNMENTS*',
        tooltip: 'List of papers assigned for review',
        click: function () {

            context.invoke('editor.insertText', '*REVIEW_ASSIGNMENTS*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var missing_reviewed_papers = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*MISSING_REVIEWED_PAPERS*',
        tooltip: 'List of papers which have outstanding reviews',
        click: function () {

            context.invoke('editor.insertText', '*MISSING_REVIEWED_PAPERS*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var reviewed_papers = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*REVIEWED_PAPERS*',
        tooltip: 'List of papers which have all review submitted',
        click: function () {

            context.invoke('editor.insertText', '*REVIEWED_PAPERS*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var paper_review = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*PAPER_REVIEW*',
        tooltip: 'Reviews of the paper',
        click: function () {

            context.invoke('editor.insertText', '*PAPER_REVIEW*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var conference_shortname = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*CONFERENCE_SHORTNAME*',
        tooltip: 'Short name of conference',
        click: function () {

            context.invoke('editor.insertText', '*CONFERENCE_SHORTNAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info btn-outline");
    return render;   // return button as jquery object
};

var conference_shortname = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*CONFERENCE_SHORTNAME*',
        tooltip: 'Short name of the conference',
        click: function () {

            context.invoke('editor.insertText', '*CONFERENCE_SHORTNAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

var name_current_user = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*NAME*',
        tooltip: 'Your name',
        click: function () {

            context.invoke('editor.insertText', '*NAME*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

var session_info = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*SESSION_INFO*',
        tooltip: 'Information of the session',
        click: function () {

            context.invoke('editor.insertText', '*SESSION_INFO*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

var schedule_page_url = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*SCHEDULE_PAGE_URL*',
        tooltip: 'Link of the conference schedule',
        click: function () {

            context.invoke('editor.insertText', '*SCHEDULE_PAGE_URL*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

var app_download_link = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*APP_DOWNLOAD_LINK*',
        tooltip: 'Links of ios and android apps',
        click: function () {

            context.invoke('editor.insertText', '*APP_DOWNLOAD_LINK*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

var session_paper_info = function (context) {
    var ui = $.summernote.ui;

    // create button
    var button = ui.button({
        contents: '*SESSION_PAPER_INFO*',
        tooltip: 'Links of papers in the session.',
        click: function () {

            context.invoke('editor.insertText', '*SESSION_PAPER_INFO*');
        }
    });

    var render = button.render();

    $(render).removeClass("btn-default").addClass("btn-info").addClass("btn-outline");
    return render;   // return button as jquery object
};

function summernote_activate(element, my_buttons, height) {
    my_buttons = (typeof my_buttons !== 'undefined') ? my_buttons : [];
    height = (typeof height !== 'undefined') ? height : 300;
    $(element).summernote({
        height: 300,
        toolbar: [
            ['font', ['fontname', 'fontsize']],
            ['style', ['bold', 'italic', 'underline', 'clear']],
            ['color', ['color']],
            ['para', ['ul', 'ol', 'paragraph']],
            ['height', ['height']],
            ['misc', ['codeview', 'undo', 'redo', 'help']],
            ['mybutton', my_buttons]
        ],
        buttons: {
            title_paper: title_paper,
            title_submission: title_submission,
            name_recipient: name_recipient,
            name_author: name_author,
            status_submission: status_submission,
            first_name_recipient: first_name_recipient,
            last_name_recipient: last_name_recipient,
            first_name_author: first_name_author,
            last_name_author: last_name_author,
            conference_name: conference_name,
            contact_email: contact_email,
            track_name: track_name,
            conference_website: conference_website,
            review_assignment: review_assignment,
            missing_reviewed_papers: missing_reviewed_papers,
            reviewed_papers: reviewed_papers,
            paper_review_system: paper_review_system,
            name_current_user: name_current_user,
            paper_review: paper_review,
            conference_shortname: conference_shortname,
            app_download_link: app_download_link,
            schedule_page_url: schedule_page_url,
            session_info: session_info,
            session_paper_info: session_paper_info
        },
        callbacks: {
            onChange: function(contents, $editable) {
                $("#email_content").val(contents);
                $("#email_content").trigger("change");
            }
        }
    });
}
