// JavaScript to handle delete comment asynchronously
$(document).ready(function () {
    // Use event delegation to handle click on delete comment button
    $(document).on("click", ".delete-comment-button", function () {
        var form = $(this).closest(".delete-comment-form");
        $.ajax({
            url: form.attr("action"),
            type: form.attr("method"),
            data: form.serialize(),
            success: function () {
                form.closest("li").remove();
            },
            error: function (xhr, status, error) {
                console.error(error);
            }
        });
    });
});

