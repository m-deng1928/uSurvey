{% load template_tags %}
first_question = function(new_data) {
	 $('#batch_questions').hide();
	 $('#quest_flow_form_cont').hide();
//	 node = cy.$('node:selected[parent]')[0];
	 $('#question_form #question').val(new_data.text);
	 $('#question_form #identifier').val(new_data.identifier);
	 $('#question_form #answer_type').val(new_data.answer_type);
	 $('#question_form').show();
}

build_new_question = function(selected_data){
 	 $('#batch_questions').hide();
 	 $('#quest_flow_form_cont').prepend('<h3 id="p_question">QUESTION ('+ selected_data.answer_type + ') >'+ selected_data.text+'</h3>');
 	 list(selected_data.answer_type);
 	 $('#validation_arg').hide();
	 $('#question_form')[0].reset();
	 $('#quest_flow_form_cont').show();
	 $('#quest_form_cont').show();
	 $('#question_form').show();
}


connect_existing_question = function(selected_data, new_data) {
	/*just create connection between the two */
    connection_id = selected_data.identifier + '_' + new_data.identifier;
	var elems = cy.add([{ group: "edges", data: { id: connection_id, source: selected_data.id, 
	                	   target: new_data.id, condition: '', validation_test: '', 
	                	   validation_arg: ['', ], } }
	                 ]);
	cy.elements().unselect();
	elems[0].select();
	$('#edit_edge').click();
	return elems;	
}

build_question_from_lib = function(selected_data, new_data) {
	 $('#batch_questions').hide();
 	 $('#quest_flow_form_cont').prepend('<h3 id="p_question">QUESTION ('+ selected_data.answer_type + ') >'+ selected_data.text+'</h3>');
 	 list(selected_data.answer_type);
 	$('#question_form')[0].reset();
 	 $('#question_form #question').val(new_data.text);
	 $('#question_form #identifier').val(new_data.identifier);
	 $('#question_form #answer_type').val(new_data.answer_type);
	 $('#quest_flow_form_cont').show();
	 $('#quest_form_cont').show();
	 $('#question_form').show();	
}

addStarterQuestion = function(new_data){
	var dat_id = new_data.identifier;
	var container_id = 'c_'+new_data.identifier;
	var new_level = 0;
	var elems = cy.add([
	                   { group: "nodes", data: { id: container_id, name: new_data.identifier , } },
	                   { group: "nodes", data: { id: dat_id, parent: container_id, level: new_level, identifier: new_data.identifier, text: new_data.text,  answer_type: new_data.answer_type}, },
	                 ]);
	elems[1].select();
	$('#submit_action').show();
	return elems;
}

addFollowUp = function(pres_question_data, new_data){
	var dat_id = new_data.identifier;
	var container_id = 'c_'+new_data.identifier;
	var connection_id = pres_question_data.identifier + '_' + new_data.identifier;
	var condition = get_condition(new_data.validation_test, new_data.validation_arg);
	var elems = cy.add([
	                   { group: "nodes", data: { id: container_id, name: new_data.identifier },},
	                   { group: "nodes",  data: { id: dat_id, parent: container_id, identifier: new_data.identifier, text: new_data.text, answer_type: new_data.answer_type}},
	                   { group: "edges", data: { id: connection_id, source: pres_question_data.id, 
	                	   target: dat_id, condition: condition, validation_test: new_data.validation_test, 
	                	   validation_arg: [new_data.validation_arg, ], } }
	                 ]);
	cy.elements().unselect();
	elems[1].select();
	return elems;
}

edit_question = function(selected, edit_data)
{
	if(selected.data('identifier') == edit_data.identifier)
	{
		selected.data('text', edit_data.text);
		selected.data('answer_type', edit_data.answer_type);
		return;
	}
	/* create new node with edit data and delete the old one. Attach selected node edges to new node */
	var dat_id = edit_data.identifier;
	var container_id = 'c_' + edit_data.identifier;
	var level = selected.data('level');
	var elems = cy.add([
	                   { group: "nodes", data: { id: container_id, name:  edit_data.identifier, }, },
	                   { group: "nodes",  data: { id: dat_id, parent: container_id, level: level, identifier: edit_data.identifier, text: edit_data.text, answer_type: edit_data.answer_type}},
	                 ]);
	cy.elements().unselect();
	elems[1].select();
	var node_edges = selected.neighborhood('edge');
	for(var i=0; i< node_edges.length; i++)
	{
		var edge = node_edges[i];
		var source = edge.data('source');
		var target = edge.data('target');
		switch(true)
		{
		case edge.data('source') == selected.data('id'):
			source = dat_id;
			break;
		case edge.data('target') == selected.data('id'):
			target = dat_id;
			break;
		}
		var connection_id = source + '_' + target;
		cy.add({ group: "edges", data: { id: connection_id, source: source, target: target, 
			condition: edge.data('condition'), validation_test: edge.data('validation_test'), 
			validation_arg: edge.data('validation_arg') } });
		edge.remove();
	}
	selected.remove();
	selected.parent().remove();

}

handle_node = function(elem_data){
	var all_nodes = cy.$('node');
//	var selected_nodes = cy.$('node:selected');
	var result = null;
	if(all_nodes.length>0 && LAST_SELECTED == undefined)
		return flash_message('No node selected');
	selected = LAST_SELECTED;
	switch(true)
	{
	case (all_nodes.length == 0):
		result = addStarterQuestion(elem_data);
		$('#cancel_question_form').click();
		break;
	case (elem_data.edit == 'true'):
		result = edit_question(selected, elem_data);
		$('#cancel_question_form').click();
		break;
	case (!elem_data.text):
		result = handle_edge(elem_data);
		$('#cancel_question_form').click();
		break;
	default:
		result = addFollowUp(selected.data(), elem_data);
	    $('#cancel_question_form').click();
	}
	
	$('#submit_action').show();
	cy.layout({
	    name: 'dagre',
	    padding: 5
	  });
	return;
}

handle_edge = function(elem_data){
	var edges = cy.$('edge:selected');
	var created = false;
	if(edges.length > 0)
	{
		edge = edges[0];
		var condition = get_condition(elem_data.validation_test, elem_data.validation_arg);
		if(condition_is_available(edge.source(), condition))
		{
			
			edge.data('condition', condition);
			edge.data('validation_test', elem_data.validation_test);
			edge.data('validation_arg', elem_data.validation_arg);
			cy.elements().unselect();
			edge.target().select();
			$('#cancel_question_form').click();
			created = true;
		}
		else{
			flash_message('Flow already exist');
		}
		$('#submit_action').show();
	}
	else
		flash_message('No Connection selected');
	edge.source().select();
	return created;
}

get_condition = function(validation_test, validation_arg)
{
	var condition = '';
	if(validation_test)
		condition = validation_test + ' ( ' +  validation_arg.join(", ") + ' )';
	return condition;
}

build_edge_form = function(edge)
{
	
	answer_type = edge.source().data('answer_type');
	list(answer_type);
	if(answer_type == 'Date Answer')
    {
    	$( "#question_flow_form .validation_arg" ).datepicker();
    }
    else 
    {
    	$( "#question_flow_form .validation_arg" ).datepicker("destroy");
    }
	$('#quest_flow_form_cont').prepend('<h3 id="p_question">QUESTION:>'+ edge.source().data('text')+'</h3>');
	$('#quest_flow_form_cont').append('<h3 id="n_question">RESPOND WITH:>'+ edge.target().data('text')+'</h3>');
}

//function to populate child select box
function list(answer_type)
{
    $("#validation_test").html(""); //reset child options
    $("#validation_test").append('<option value="">------ is anything ------------</option>');
    array_list = QUES_VALIDATION_OPTS[answer_type];
    $(array_list).each(function (i) { //populate child options
        $("#validation_test").append("<option value=\""+array_list[i].value+"\">"+array_list[i].display+"</option>");
    });
}

identify_is_available = function(identifier) {
	identifier = identifier.trim();
	var i = 0;
	var nodes = cy.$('node[parent]');
	selected_node = cy.$('node:selected[parent]')[0];
	var edit = $('#question_form').attr('edit') == 'true';
	var available = true;
	if((edit && selected_node.data('identifier') == identifier) == false)
		for (; i < nodes.length; i++) 
	    {   
			if((identifier) == nodes[i].data('identifier'))
	    	{
	    		available = false;
	    	}
	    }
	return available;
}

condition_is_available = function(source, condition) {
	var source_id = source.data('id');
	var node_edges = source.neighborhood('edge[source="'+source_id+'"]');
	for (var i = 0; i < node_edges.length; i++) 
    {   
    	if(condition.trim() == node_edges[i].data('condition'))
    		return false;
    }
	return true;
}

is_neighbour_node = function(source, dest) {
	return source.edgesWith(dest).length > 0;
}


flash_message = function(msg) {
	alert(msg);
}

//dialog = $( "#question_form" ).dialog({
//	autoOpen: false,
//	height: 300,
//	width: 350,
//	modal: true,
//	buttons: {
//		"Add": function(){ alert('submit meehn');},
//		Cancel: function() {
//			dialog.dialog( "close" );
//		}
//	},
//	close: function() {
//		form[ 0 ].reset();
//		allFields.removeClass( "ui-state-error" );
//	}
//});