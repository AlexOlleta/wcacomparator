function $_GET(variable){
	var query = window.location.search.substring(1);
	var vars = query.split("&");
	for (var i=0;i<vars.length;i++) {
		var pair = vars[i].split("=");
		if(pair[0] == variable){return pair[1];}
	}
	return(false);
}

function isWCAId(value){
	if (typeof parseInt(value.substring(0,1)) == "number" && !isNaN(parseInt(value.substring(0,1))) ){
		var iswcaid = true;
	}
	else{
		var iswcaid = false;
	}
	return iswcaid;
}

/*$('#wcaid-submenu a').click(function(e){
  e.preventDefault();
  $(this).tab('show');
});*/

$('#get-wcaid-country').click(function(){
    $(this).text("Loading...");
	var wcaidcountry = $('#wcaid-country').val();
	localStorage.setItem("iswcaid",isWCAId(wcaidcountry));

	window.location.href = "find?id="+wcaidcountry;
});

var show_output = function(){
	if ($_GET("id")==""){
		//alert("No has introducido nada.");
		$('#output-wcaid').hide();
		$('#output-country').hide();
	}
	var iswcaid = (isWCAId($_GET("id")) || (localStorage.getItem("iswcaid") === "true"));
	//var pncomps = (false || (localStorage.getItem("pncomps") === "true"));
	/*var plogros = (false || (localStorage.getItem("plogros") === "true"));

	var ccomps = (false || (localStorage.getItem("ccomps") === "true"));
	var cnrs = (false || (localStorage.getItem("cnrs") === "true"));
	var top100 = (false || (localStorage.getItem("top100") === "true"));*/

	if(iswcaid){
		$('#output-wcaid').show();
		$('#output-country').hide();
	}
	else if(!iswcaid){
		$('#output-wcaid').hide();
		$('#output-country').show();
	}
	else{
		$('#output-wcaid').hide();
		$('#output-country').hide();
		$('#output-comps').hide();
	}

};


$("#evo").hide();
$(".loader").hide();

$(".graph").click(function(){
	cat = $(this).val();
    if(cat.substr(0,3) == "sgl"){
        kind = "Single";
        alert(kind);
    }
    else if(cat.substr(0,3) == "avg"){
        kind = "Average"
        alert(kind);
    }
    else{
	   chart_json(cat);
    }
});

var chart_json = function(evento){
    $(".loader").fadeIn("fast");
    $.ajax({
        type: 'GET',
        url: './chart_json.json?id1=' + $_GET("id") + '&cat1=' + evento,
        //dataType: 'json'
    })
    .done(function(json){
        //alert("buu");
        labels_list = JSON.parse(json.labels.replace(/'/g, '"'));
        bests_list = JSON.parse(json.bests.replace(/'/g, '"'));
        avgs_list = JSON.parse(json.averages.replace(/'/g, '"'));

        show_chart(evento, labels_list, bests_list, avgs_list);
    })
    .fail(function(xhr, status, error) {
        //show_output_error();
        console.log('Ajax Error!');
        console.log(xhr.status + ': ' + xhr.statusText);
        console.log(status + ': ' + error);
    });
};


function show_chart(evento, labels, bests, averages){
    var data = {
        "labels": labels,
        "datasets": [
            {
                "label": evento + " Bests Evolution",
                "fill": false,
                "lineTension": 0.1,
                "backgroundColor": "rgba(153,255,51,0.4)",
                "borderColor": "#57A639",
                "borderCapStyle": "butt",
                "borderDash": [],
                "borderDashOffset": 0.0,
                "borderJoinStyle": "miter",
                "pointBorderColor": "rgba(153,255,51,1)",
                "pointBackgroundColor": "#000",
                "pointBorderWidth": 1,
                "pointRadius": 3,
                "pointHoverRadius": 6,
                "pointHoverBackgroundColor": "rgba(153,255,51,1)",
                "pointHoverBorderColor": "rgba(220,220,220,1)",
                "pointHoverBorderWidth": 2,
                "pointHitRadius": 10,
                "data": bests
            },
            {
                "label": evento + " Averages Evolution",
                "fill": false,
                "lineTension": 0.1,
                "backgroundColor": "rgba(75,192,192,0.4)",
                "borderColor": "rgba(75,192,192,1)",
                "borderCapStyle": "butt",
                "borderDash": [],
                "borderDashOffset": 0.0,
                "borderJoinStyle": "miter",
                "pointBorderColor": "rgba(75,192,192,1)",
                "pointBackgroundColor": "#000",
                "pointBorderWidth": 1,
                "pointRadius": 3,
                "pointHoverRadius": 6,
                "pointHoverBackgroundColor": "rgba(75,192,192,1)",
                "pointHoverBorderColor": "rgba(220,220,220,1)",
                "pointHoverBorderWidth": 2,
                "pointHitRadius": 10,
                "data": averages
            }
        ]
    }

    $(".loader").fadeOut("fast");
    var zone = $("#evo");
    zone.show();
    mychart = new Chart(zone, {type: 'line', data: data});
}

function show_nr_chart(evento, kind, labels, data){
    var data = {
        "labels": labels,
        "datasets": [
            {
                "label": evento + kind + "'s' NRs' Evolution",
                "fill": false,
                "lineTension": 0.1,
                "backgroundColor": "rgba(153,255,51,0.4)",
                "borderColor": "#57A639",
                "borderCapStyle": "butt",
                "borderDash": [],
                "borderDashOffset": 0.0,
                "borderJoinStyle": "miter",
                "pointBorderColor": "rgba(153,255,51,1)",
                "pointBackgroundColor": "#000",
                "pointBorderWidth": 1,
                "pointRadius": 3,
                "pointHoverRadius": 6,
                "pointHoverBackgroundColor": "rgba(153,255,51,1)",
                "pointHoverBorderColor": "rgba(220,220,220,1)",
                "pointHoverBorderWidth": 2,
                "pointHitRadius": 10,
                "data": data
            }
        ]
    }

    $(".loader").fadeOut("fast");
    var zone = $("#evo");
    zone.show();
    mychart = new Chart(zone, {type: 'line', data: data});
}