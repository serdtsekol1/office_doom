$(document).ready(function () {
    $('#sidebarCollapse').on('click', function () {
        $('#sidebar').toggleClass('active');
    });
});

$("#save_product").on('click', (e) => {
    $.ajax({
        type: "POST",
        url: 'save_product/',
        data: {
            'price': $("#price").val(),
            'code': $("#code").val(),
        },
        async: false,
        success: function (data) {
            console.log(data)
        }
    });
})

$("#form_file").on('submit', (e) => {
    e.preventDefault()
    console.log('test')
    let fd = new FormData();
    let files = $('#file')[0].files[0];
    fd.append('file', files);
    fd.append('company', $("#company :selected").val());
    $.ajax({
        type: "POST",
        url: '/manual_invoice/',
        data: fd,
        contentType: false,
        processData: false,
        async: false,
        success: function (data) {
            console.log(data)
        }
    });
})
$("#form_show_excel_document").on('submit', (e) => {
    e.preventDefault()
    console.log('test')
    let fd = new FormData();
    let files = $('#file')[0].files[0];
    fd.append('file', files);
    $.ajax({
        type: "POST",
        url: '/show_excel_document/',
        data: fd,
        contentType: false,
        processData: false,
        async: false,
        success: function (data) {
            $("#document_html").html(data.document_html)
        }
    });
})


$(".one_cell").on("click", (e) => {
    const id_input = `#input_${$("input[name='type_cell']:checked").attr('id')}`
    $(id_input).val(`${e.currentTarget.dataset.id_row},${e.currentTarget.dataset.id}`)
    console.log(id_input)
})

$("#form_preset").on('submit', (e) => {
    e.preventDefault()
    let data = $("#form_preset").serializeArray().reduce(function (obj, item) {
        console.log(item)
        if (obj[item.name]) {
            obj[item.name] += `,${item.value}`;
        } else {
            obj[item.name] = item.value;
        }
        return obj;
    }, {});
    console.log(data)
    $.ajax({
        type: "POST",
        url: '/preset/',
        data: data,
        // contentType: "application/json",
        success: function (data) {
            if (data.success) {
                alert('Гуд')
            } else {
                alert('Заповни всі поля')
            }
        }
    });
})
