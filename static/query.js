var show = 0;
$("#query_result").val("");

$('#check_query').click(function(){
	var query = $('#query').val();

	alert(query);
    var titles = query.substr(query.indexOf("SELECT") + 7, query.indexOf("FROM") - 7);
	query_json(titles, query);
});

var query_json = function(titles, query) {
    $.ajax({
        type: 'GET',
        url: './query_json.json?q=' + query + '&t=' + titles,
        dataType: 'json'
    })
    .done(function(json) {
        alert(json.title);
        var quer = json.sql;
        var output = "";
        output += json.title + "\n";
        output += "-".repeat(200) + "\n";
        for (var i=1; i<Object.keys(quer).length+1; i++){
            var list = quer[i.toString()];
            if (typeof list === 'undefined') list = "";
            output += list + "\n";
        }

        $('#query_result').val(output);
    })
    .fail(function(xhr, status, error) {
        //show_output_error();
        console.log('Ajax Error!');
        console.log(xhr.status + ': ' + xhr.statusText);
        console.log(status + ': ' + error);
    });
};


$(".panel-body").hide();

$(".panel-heading").click(function(){
    var hid = $(this).attr("href");
    if (show == 0){
        $(hid).fadeIn();
        show = 1;
    }
    else{
        $(hid).hide();
        show = 0;
    }
});

$("#morequeries").hide();

$("#evenmore_queries").click(function(){
    $("#morequeries").show();
})

$(".copy").click(function(){
    var item = "#" + $(this).parent().attr("id");
    copyToClipboard(item);
    alert("The query has been copied to your clipboard.");
});

function copyToClipboard(element) {
    var $temp = $("<input>");
    $("body").append($temp);
    $temp.val($(element).text().slice(0,-20)).select();
    document.execCommand("copy");
    $temp.remove();
}