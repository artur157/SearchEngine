document.onclick = function(event) {
    document.getElementById('complete-list').innerHTML = '';
};

function redirectQuery(query) {
	document.getElementById('query-field').value = query;
	window.location.href = "http://localhost:8000/cgi-bin/search_engine.py?query=" + query + "&submit=Поиск";
}

function showSuggestAsync() {
  var xhr = new XMLHttpRequest();
  xhr.open('POST', 'http://localhost:9200/kubsu1/_search', true);
  xhr.setRequestHeader("Content-type", "application/json; charset=UTF-8");
  user_input = document.getElementById('query-field').value;
  competion_prefix = user_input.substring(user_input.indexOf(' '));
  
  req_body = {'query':
                 {'match_phrase_prefix':
                      {'body': {
						  'query': competion_prefix
					  }}},
             'aggregations': {
                 'completion': {
                     'terms': {
                         'field': 'completion',
                         'include': user_input + '.*'
             }}}}
			 
  xhr.onreadystatechange = function(){
	  if(xhr.readyState == 4 && xhr.status == 200){
	      var response = JSON.parse(xhr.responseText);
		  
		  var output = '<ul>';
		  response['aggregations']['completion']['buckets'].forEach(item => {
			  output += '<li class="complete-li" onclick="redirectQuery(' + '\'' + item['key'] + '\'' + ');">' + item['key'] + '</li>';
		  });
		  output += '</ul>';
		  
		  if (output != ''){
			  document.getElementById('complete-list').innerHTML = output;

		  }
		
	  }
  }

  xhr.send(JSON.stringify(req_body));
}

function showSimilarDocs(order_num, vector){
	if(!document.getElementById('sim-docs-' + order_num)){
		
		b_all_zeros = true;
		vector.forEach(item => {
			if (item != 0){
				b_all_zeros = false
			}
		});
		
		
		if(!b_all_zeros){
			
			var xhr = new XMLHttpRequest();
			xhr.open('POST', 'http://localhost:9200/kubsu1/_search', true);
			xhr.setRequestHeader("Content-type", "application/json; charset=UTF-8");

			zero_vector = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
				0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
				0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

			req_body = {"_source": ["title", "url", "body_vector"],
						"query": {
							"script_score": {
								"query": {"match_all": {}},
								"script": {
									"source": "l1norm(params.zero_vector, doc['body_vector']) == 0 ? 0 : cosineSimilarity(params.query_vector, doc['body_vector']) + 1.0",
									"params": {"query_vector": vector,
											   "zero_vector": zero_vector}
								}
							}
						},
						'size': 5}
					 
			xhr.onreadystatechange = function(){
			  if(xhr.readyState == 4 && xhr.status == 200){
				  var response = JSON.parse(xhr.responseText);
				  
				  var output = '<div class="stroka-sim-doc center">похожие документы</div><ul id="sim-docs-' + order_num + '" class="inline">';
				  //alert('1');
				  for (var i = 1; i < response['hits']['hits'].length; i++) {
					  item = response['hits']['hits'][i];
					  output += '<li><p class="clip"><a href="' + item['_source']['url'] + '" target="_blank">' + item['_source']['title'] + '</a></p><br>' +
					              '<div class="green"><p class="clip"><a href="' + item['_source']['url'] + '" target="_blank">' + item['_source']['url'] + '</a></p></div></li>';
				  };
				  output += '</ul>';
				  
				  if (output != ''){
					  document.getElementById('div' + order_num).innerHTML += output;

				  }
				
			  }
			}

			xhr.send(JSON.stringify(req_body));
	  
	  
			//document.getElementById('div' + order_num).innerHTML += '<br><br><div id="sim-docs-' + order_num + '">123<br>234<br>345<br>456</div>';
		
		}
	}
}

function checkRadio(param){
	if (param == 0){
		// деактивируем все чекбоксы
		deactiveCheckboxes(true);
	}
	else{
		// активируем все чекбоксы
		deactiveCheckboxes(false);
	}
}

function deactiveCheckboxes(param){
 var inputs=document.getElementsByTagName('input');
 for(var i=0;i<inputs.length;i++)
 {
  if(inputs[i].type=='checkbox')
  {
   inputs[i].disabled = param;
  }
 }
}