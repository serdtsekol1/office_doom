$(document).ready(() => {
//#region Створення ТАБІВ
    let html = "<div class='tabs'>"
    $("form > div > fieldset > h2, form > div > .js-inline-admin-formset fieldset.module > h2").each((key, val) => {
        // console.log($(val).parent()[0].fild
        if (key === 0) {
            html += `<div class="tab active ${$(val).parent()[0].className}" data-id="${key}">${val.innerText}</div>`
            $(val).parent().show();
        } else {
            html += `<div class="tab ${$(val).parent()[0].className}" data-id="${key}">${val.innerText}</div>`
            $(val).parent().hide();
        }
    })
    html += "</div>"
    $("form").before(html)
//#endregion Створення ТАБІВ
    //
    $('.tabs > .tab').on('click', (e) => {
        $('.tabs > .tab').removeClass('active');
        $(e.currentTarget).addClass('active');
        $(`form > div > fieldset, form > div > .js-inline-admin-formset fieldset.module`).each((key, val) => {
            if (key === $(e.currentTarget).data('id')) {
                $(val).show();
            } else {
                $(val).hide();
            }

        })
    })
})