$('#btinver').click(function(){
	$(this).text("Loading...");
	var wcain = $('#wcaid-country-in1').val();
	window.location.href = "find?id="+wcain;
})

$('#btincomp').click(function(){
	$(this).text("Loading...");
	var wcain1 = $('#wcaid-country-in1').val();
	var wcain2 = $('#wcaid-country-in2').val();
	window.location.href = "compare?id1="+wcain1+"&id2="+wcain2;
})