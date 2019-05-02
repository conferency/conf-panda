/*
 $("form").submit(function (event) {
 if (document.getElementById('email').validity.valid) {
 $("#email-error").html("").parent().removeClass("has-error");
 } else {
 event.preventDefault();
 $("#email-error").html("Invalid email address.").parent().addClass("form-group has-error");
 globalError.push({msg:"Failed to valid email"});
 }
 }, false);

 $("#email").blur(function (e) {
 if (document.getElementById('email').validity.valid) {
 $("#email-error").html("").parent().removeClass("has-error");
 } else {
 $("#email-error").html("Invalid email address.").parent().addClass("form-group has-error");
 }
 });*/
var form = document.getElementsByTagName('form')[0];
var email = document.getElementById('email');
var error = document.getElementById('email-error');
email.addEventListener("blur", function (event) {
    if (email.validity.valid) {
        error.innerHTML = ""; // Reset the content of the message
        error.parentNode.className = "form-group";
    } else {
        error.innerHTML = "Invalid email address.";
        error.parentNode.className = "form-group has-error";
    }
}, false);

form.addEventListener("submit", function (event) {
    email.checkValidity();
    if (!email.validity.valid) {
        // Prevent the form to be submitted if email invalid.
        event.preventDefault();
    }
}, false);
