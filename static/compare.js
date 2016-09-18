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

$('#get-wcaids-countries').click(function(){
	$(this).text("Loading...");
	var wcaidcountry1 = $('#wcaid-country1').val();
	var wcaidcountry2 = $('#wcaid-country2').val();

	localStorage.setItem("iswcaid1",isWCAId(wcaidcountry1));
	localStorage.setItem("iswcaid2",isWCAId(wcaidcountry2));

	window.location.href = "compare?id1="+wcaidcountry1+"&id2="+wcaidcountry2;
});

var show_output = function(){
	if ($_GET("id1")=="" && $_GET("id2")==""){
		//alert("No has introducido nada.");
		$('#output-wcaids').hide();
		$('#output-countries').hide();
	}

	var iswcaid1 = (isWCAId($_GET("id1")) || (localStorage.getItem("iswcaid1") === "true"));
	var iswcaid2 = (isWCAId($_GET("id2")) || (localStorage.getItem("iswcaid2") === "true"));

	if(iswcaid1 && iswcaid2){
		$('#output-wcaids').show();
		$('#output-countries').hide();
	}
	else if(!iswcaid1 && !iswcaid2){
		$('#output-wcaids').hide();
		$('output-countries').show();
	}
	else{
		$('#output-wcaids').hide();
		$('#output-countries').hide();
	}	
};


$('#nemesis').click(function(){
	$("#isnemesis").show();
})