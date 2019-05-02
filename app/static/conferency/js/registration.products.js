function option_convert(option) {
    // convert string into array
    if (typeof option === 'string') {
        option = option.replace(/[\']/g, '\"').replace(/u\"/g, '\"');
        return JSON.parse(option);
    } else {
        return option;
    }
}

function delete_product_option(obj){
    // get option num in option price
    option = obj.parentNode.previousSibling.childNodes[1];
    option_count = option.id.split('_').slice(-1)[0];
    var li = option.parentNode.parentNode.parentNode;
    ul = li.parentNode;
    ul.removeChild(li);
    option_count++;
    var current_new_option=document.getElementById("new_option_name_"+option_count);
    while(current_new_option!=null){
        var current_new_option_price = document.getElementById("new_option_price_"+option_count);
        current_new_option.id="new_option_name_"+(option_count-1);
        current_new_option.name="new_option_name_"+(option_count-1);
        current_new_option_price.id="new_option_price_"+(option_count-1);
        current_new_option_price.name="new_option_price_"+(option_count-1);
        option_count++;
        current_new_option=document.getElementById("new_option_name_"+option_count);
    }

    if (document.querySelectorAll('input[name*="option_name_"]').length === 0) {
        document.getElementById("product_price").disabled = false;
    }
}

function usage_limit(element) {
    var with_limit = document.getElementById("usage_limit_type_with_limit");
    with_limit.checked = true;
    with_limit.value = element.value;
    if (!element.value) {
        with_limit.value = 0;
    } else {
        with_limit.value = element.value;
    }
    // console.log(with_limit.value);
}

function add_product_option() {
    // console.log(element);
    var ul = document.getElementById("product_options_list");
    var ocount=0;
    while(document.getElementById("new_option_name_"+ocount)!=null)ocount++;
    if (ocount === 0) {
        document.getElementById("product_price").disabled = true;
    }
    var li = document.createElement("li");
    li.setAttribute("onmouseover","show_buttons(this,1)");
    li.setAttribute("onmouseout","hide_buttons(this,1)");
    li.setAttribute("class","row padding-bottom-5");
    // li.innerHTML="<input data-option-id=\"\" class=\"col-md-7 form-control required\" type=\"text\" id=\"new_option_"+ocount+"\" name=\"new_option_"+ocount+"\" placeholder=\"new option\"/>"+"<div style=\"display:none\" class=\"col-md-5 option_button\">"+"<span class=\"btn glyphicon glyphicon-trash\" onclick=\"delete_option(this)\"></span></div>";
    li.innerHTML='<div class="form-inline"><div class="form-group"><label for="new_option_name_'+ocount+'" class="sr-only">New option</label><input type="text" placeholder="Enter option name" id="new_option_name_'+ocount+'" name="new_option_name_'+ocount+'" class="form-control required option-name" data-option-id=""></div> <div class="form-group input-group"><label for="new_option_price_'+ocount+'" class="sr-only">Enter the price</label><input type="text" placeholder="Enter the price" id="new_option_price_'+ocount+'" name="new_option_price_'+ocount+'" class="form-control check_price" data-option-id="" value="'+document.getElementById("product_price").value+'"></div><div style="display: none;" class="option_button form-group"><span class="btn glyphicon glyphicon-trash" onclick="delete_product_option(this)"></span></div><br></div>';
    ul.appendChild(li);
}

function delete_product(element) {
    var product_ele = element.parentNode.parentNode.parentNode;
    swal({
        title: "Are you sure?",
        text: "You will not be able to recover this product!",
        type: "warning",
        showCancelButton: true,
        confirmButtonColor: "#DD6B55",
        confirmButtonText: "Yes, delete it!",
        closeOnConfirm: false },
        function() {
            $.ajax({
                type: "DELETE",
                url: endpoints.deleteProduct,
                contentType: "application/json",
                data: JSON.stringify({'delete_ticket_id': product_ele.getAttribute("data-product-id")}),
                success: function (response) {
                    swal("Deleted!", "This product has been deleted.", "success");
                    product_ele.parentNode.removeChild(product_ele);
                }
            })
                .fail(function(data, textStatus, error) {
                    // console.log(data);
                    swal({title: "Oops...", text: "Update failed. Please refreash the page.", type: "error", timer: 2000,   showConfirmButton: false});
            });
        }
    );
}

function update_product_statue(element) {
    element.disabled = true;
    var product_ele = element.parentNode.parentNode.parentNode;
    if (element.getAttribute("data-product-status") === 'Normal') {
        var next_status = "Hided";
    } else {
        var next_status = "Normal";
    }
    $.ajax({
            type: "PUT",
            url: endpoints.updateProduct + product_ele.getAttribute("data-product-id"),
            contentType: "application/json",
            data: JSON.stringify({'update': 'status', 'status': next_status}),
            success: function (response) {
                // update status
                element.setAttribute("data-product-status", response.status);
                element.classList.toggle("glyphicon-eye-close");
                element.classList.toggle("glyphicon-eye-open");
                element.setAttribute("title", (response.status == 'Normal' ? "Hide this product" : "Show this product"));
            }
        })
            .fail(function(data, textStatus, error) {
                // console.log(data);
                swal({title: "Oops...", text: "Update failed. Please refreash the page.", type: "error", timer: 2000,   showConfirmButton: false});
        })
            .always(function() {
                element.disabled = false;
            });
}

(function () {
    // price validator
    jQuery.validator.addMethod("positive_number", function(value, el, param) {
        return value >= 0;
    }, "The input value must be positive number");
    // option validator

    jQuery.validator.classRuleSettings.check_price = { positive_number: true, required: true };
    jQuery.validator.classRuleSettings.positive_number = { positive_number: true };
    $('#product-modal-form').validate({
        errorPlacement: function(error, element) {
            // for product price
            if(element.hasClass('check_price') || element.hasClass('option-name')) {
                error.appendTo(element.parent().parent());
            } else {
                error.appendTo(element.parent());
            }
        }
    });

    $("#productModal").on("show.bs.modal", function (event) {
        var action = $(event.relatedTarget).attr('data-action');
        // datepicker can also fire this function. this can avoid that
        if (typeof action === "undefined") {
            return;
        }
        var modal = $(this);
        // clean the form
        modal.find('.modal-form')[0].reset();
        // remove all li in ul
        modal.find('#product_options_list').empty();
        if (action === "edit_product") {
            var product_div = $(event.relatedTarget).parent().parent().parent();
            // update method of the form
            modal.find('#_method').val('put');
            // if use attr('value', ). reset() won't work
            modal.find('#product_id').val(product_div.attr('data-product-id'));
            modal.find('#product_name').val(product_div.find('h5').attr('data-product-name'));
            if (product_div.find('.product_price').attr('data-product-price') === 'None') {
                modal.find('#product_price').attr("disabled", true);
            } else {
                modal.find('#product_price').val(product_div.find('.product_price').attr('data-product-price'));
                modal.find('#product_currency').val(product_div.find('.product_price').attr('data-product-currency'));
            }
            if (product_div.find('.product_inventory').attr('data-product-inventory') === '-1') {
                modal.find("#usage_limit_type_no_limit").attr("checked", true);
            } else {
                modal.find("#usage_limit_type_with_limit").attr("checked", true);
                modal.find("#usage_limit_type_with_limit").val(product_div.find('.product_inventory').attr('data-product-inventory'));
                modal.find("input[name=inventory]").val(product_div.find('.product_inventory').attr('data-product-inventory'));
            }
            product_div.find('code').each(function(index) {
                var $option = $('<li onmouseover="show_buttons(this,1)" onmouseout="hide_buttons(this,1)" class="row padding-bottom-5"><input class="col-md-7 form-control required" type="text" id="option_' + $(this).data('option-id') + '" name="option_' + $(this).data('option-id') + '" placeholder="Option name" value="' + $(this).data('option-name') + '"><div style="display: none;" class="col-md-5 option_button"><span class="btn glyphicon glyphicon-trash" onclick="delete_option(this)"></span></div></li>');
                var $option = $('<li onmouseover="show_buttons(this,1)" onmouseout="hide_buttons(this,1)" class="row padding-bottom-5"><div class="form-inline"><div class="form-group"><input type="text" placeholder="Enter option name" id="option_name_'+ index +'" name="option_name_'+$(this).data('option-id')+'" class="form-control required option-name" data-option-id="'+$(this).data('option-id')+'" value="'+$(this).data('option-name')+'"></div> <div class="form-group input-group"><span class="input-group-addon">$</span><input type="text" placeholder="Enter the price" id="option_price_'+$(this).data('option-id')+'" name="option_price_'+$(this).data('option-id')+'" class="form-control check_price" data-option-id="'+$(this).data('option-id')+'" value="'+$(this).data('option-price')+'"></div><div style="display: none;" class="option_button form-group"><span class="btn glyphicon glyphicon-trash" onclick="delete_product_option(this)"></span></div><br></div></li>');
                $('#product_options_list').append($option);
            })
        } else if (action === "new_product") {
            modal.find('#_method').val('post');
            modal.find('#product_id').val('');
        }
    });

    $('#productModal').on("hidden.bs.modal", function (event) {
        $(this).find('#product_price').attr("disabled", false);
    });
}());
