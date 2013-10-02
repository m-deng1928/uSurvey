from django.test import TestCase
from survey.forms.logic import LogicForm
from survey.models import Question, Batch, QuestionOption, AnswerRule


class LogicFormTest(TestCase):
    def test_knows_the_fields_in_form(self):
        logic_form = LogicForm()

        fields = ['condition', 'attribute', 'option', 'value', 'validate_with_question', 'action', 'next_question']
        [self.assertIn(field, logic_form.fields) for field in fields]

    def test_does_not_have_value_and_validate_question_if_question_has_options(self):
        fields = ['value', 'validate_with_question']
        batch = Batch.objects.create(order=1)
        question_with_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.MULTICHOICE, order=1)
        question_with_option.batches.add(batch)
        logic_form = LogicForm(question=question_with_option, batch=batch)
        [self.assertNotIn(field, logic_form.fields) for field in fields]

    def test_does_not_have_option_if_question_does_not_have_options(self):
        field = 'option'
        batch = Batch.objects.create(order=1)
        question_without_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.NUMBER, order=1)
        question_without_option.batches.add(batch)
        logic_form = LogicForm(question=question_without_option, batch=batch)
        self.assertNotIn(field, logic_form.fields)

    def test_choice_of_attribute_is_value_and_validate_with_question_if_question_does_not_have_options(self):
        batch = Batch.objects.create(order=1)
        question_without_option = Question.objects.create(text="Question 1?",
                                                          answer_type=Question.NUMBER, order=1)
        question_without_option.batches.add(batch)
        attribute_choices = [('value', 'Value'), ('validate_with_question', "Question")]
        logic_form = LogicForm(question=question_without_option, batch=batch)
        self.assertEqual(2, len(logic_form.fields['attribute'].choices))
        [self.assertIn(attribute_choice, logic_form.fields['attribute'].choices) for attribute_choice in attribute_choices]

    def test_choice_of_attribute_is_option_if_question_has_options(self):
        batch = Batch.objects.create(order=1)
        question_with_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.MULTICHOICE, order=1)
        question_with_option.batches.add(batch)

        attribute_choice = ('option', 'Option')
        logic_form = LogicForm(question=question_with_option, batch=batch)
        self.assertEqual(1, len(logic_form.fields['attribute'].choices))
        self.assertIn(attribute_choice, logic_form.fields['attribute'].choices)

    def test_label_of_condition_has_question_text(self):
        field = 'condition'
        batch = Batch.objects.create(order=1)
        question_without_option = Question.objects.create(text="Question 1?",
                                                          answer_type=Question.NUMBER, order=1)
        question_without_option.batches.add(batch)

        logic_form = LogicForm(question=question_without_option, batch=batch)
        self.assertIn(question_without_option.text, logic_form.fields[field].label)

    def test_option_field_is_prepopulatad_with_question_options_if_selected_question_is_multi_choice(self):
        field = 'option'
        batch = Batch.objects.create(order=1)
        question_with_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.MULTICHOICE, order=1)
        question_with_option.batches.add(batch)
        question_option_1 = QuestionOption.objects.create(question=question_with_option, text="Option 1", order=1)
        question_option_2 = QuestionOption.objects.create(question=question_with_option, text="Option 2", order=2)
        question_option_3 = QuestionOption.objects.create(question=question_with_option, text="Option 3", order=3)

        logic_form = LogicForm(question=question_with_option, batch=batch)
        all_options = [question_option_1, question_option_2, question_option_3]
        option_choices = logic_form.fields[field].choices

        self.assertEqual(3, len(option_choices))
        [self.assertIn((question_option.id, question_option.text), option_choices) for question_option in all_options]

    def test_action_field_has_all_actions_on_load_irrespective_of_question(self):
        field = 'action'
        logic_form = LogicForm()
        skip_to = ('SKIP_TO', 'JUMP TO')
        end_interview = ('END_INTERVIEW', 'END INTERVIEW')
        reconfirm = ('REANSWER', 'REANSWER')
        ask_subquestion = ('ASK_SUBQUESTION', 'ASK SUBQUESTION')

        all_actions = [skip_to, end_interview, reconfirm, ask_subquestion]
        action_choices = logic_form.fields[field].choices
        self.assertEqual(4, len(action_choices))
        [self.assertIn(action, action_choices) for action in all_actions]

    def test_choices_for_condition_field_knows_equals_option_is_choice_if_multichoice(self):
        choices_returned = LogicForm().choices_for_condition_field(is_multichoice=True)

        self.assertEqual(1,len(choices_returned))
        self.assertIn(('EQUALS_OPTION', 'EQUALS_OPTION'), choices_returned)
        self.assertNotIn(('EQUALS', 'EQUALS'), choices_returned)

    def test_choices_for_condition_field_does_not_know_equals_option_is_choice_if_not_multichoice(self):
        choices_returned = LogicForm().choices_for_condition_field(is_multichoice=False)

        self.assertEqual(5,len(choices_returned))
        self.assertNotIn(('EQUALS_OPTION', 'EQUALS_OPTION'), choices_returned)

    def test_condition_field_should_have_equals_option_if_multichoice_question(self):
        field = 'condition'
        batch = Batch.objects.create(order=1)
        question_with_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.MULTICHOICE, order=1)
        question_with_option.batches.add(batch)
        logic_form = LogicForm(question=question_with_option, batch=batch)

        self.assertEqual(1,len(logic_form.fields[field].choices))
        self.assertIn(('EQUALS_OPTION', 'EQUALS_OPTION'), logic_form.fields[field].choices)
        self.assertNotIn(('EQUALS', 'EQUALS'), logic_form.fields[field].choices)

    def test_condition_field_should_not_have_equals_option_if_not_multichoice_question(self):
        field = 'condition'
        batch = Batch.objects.create(order=1)
        question_without_option = Question.objects.create(text="Question 1?",
                                                       answer_type=Question.NUMBER, order=1)

        question_without_option.batches.add(batch)
        logic_form = LogicForm(question=question_without_option, batch=batch)
        self.assertEqual(5, len(logic_form.fields[field].choices))
        self.assertNotIn(('EQUALS_OPTION', 'EQUALS_OPTION'), logic_form.fields[field].choices)

    def test_next_question_knows_all_sub_questions_if_data_sent_with_action_ask_subquestion(self):
        field = 'next_question'

        batch = Batch.objects.create(order=1)
        question_without_option = Question.objects.create(batch=batch, text="Question 1?",
                                                          answer_type=Question.NUMBER, order=1)

        sub_question1 = Question.objects.create(batch=batch, text="sub question1", answer_type=Question.NUMBER,
                                                subquestion=True, parent=question_without_option)

        data= {'action': 'ASK_SUBQUESTION'}
        logic_form = LogicForm(question=question_without_option,data=data, batch=batch)

        self.assertIn((sub_question1.id,sub_question1.text), logic_form.fields[field].choices)

    def test_should_not_add_answer_rule_twice_on_same_option_of_multichoice_question(self):
        batch = Batch.objects.create(order=1)
        question_1 = Question.objects.create(batch=batch, text="How many members are there in this household?",
                                                 answer_type=Question.MULTICHOICE, order=1)
        option_1_1 = QuestionOption.objects.create(question=question_1, text="OPTION 1", order=1)
        option_1_2 = QuestionOption.objects.create(question=question_1, text="OPTION 2", order=2)

        sub_question_1 = Question.objects.create(batch=batch, text="Specify others", answer_type=Question.TEXT,
                                                 subquestion=True, parent=question_1)

        rule = AnswerRule.objects.create(action=AnswerRule.ACTIONS['ASK_SUBQUESTION'],
                                         condition=AnswerRule.CONDITIONS['EQUALS_OPTION'],
                                         validate_with_option=option_1_1, next_question=sub_question_1, batch=batch)

        data = dict(action=rule.action,
                    condition=rule.condition,
                    option=rule.validate_with_option, next_question=rule.next_question)

        logic_form = LogicForm(question = question_1, data = data, batch=batch)

        self.assertFalse(logic_form.is_valid())

    def test_should_not_add_answer_rule_twice_on_same_value_of_numeric_question(self):
        batch = Batch.objects.create(order=1)
        question_1 = Question.objects.create(batch=batch, text="How many members are there in this household?",
                                                 answer_type=Question.NUMBER, order=1)
        value_1 = 0
        value_2 = 20

        sub_question_1 = Question.objects.create(batch=batch, text="Specify others", answer_type=Question.TEXT,
                                                 subquestion=True, parent=question_1)

        rule = AnswerRule.objects.create(question=question_1, action=AnswerRule.ACTIONS['ASK_SUBQUESTION'],
                                         condition=AnswerRule.CONDITIONS['EQUALS'],
                                         validate_with_value=value_1, next_question=sub_question_1, batch=batch)

        data = dict(action=rule.action,
                    condition=rule.condition,
                    value=rule.validate_with_value, next_question=rule.next_question)

        logic_form = LogicForm(question = question_1, data = data, batch=batch)

        self.assertFalse(logic_form.is_valid())

        another_data = dict(action=AnswerRule.ACTIONS['END_INTERVIEW'],
                    condition=AnswerRule.CONDITIONS['GREATER_THAN_VALUE'],
                    value=rule.validate_with_value)

        logic_form = LogicForm(question = question_1, data = another_data, batch=batch)

        self.assertTrue(logic_form.is_valid())

    def test_should_not_add_answer_rule_twice_on_same_question_value_of_numeric_question(self):
        batch = Batch.objects.create(order=1)
        question_1 = Question.objects.create(batch=batch, text="How many members are there in this household?",
                                             answer_type=Question.NUMBER, order=1)

        question_2 = Question.objects.create(batch=batch, text="How many members are above 18 years?",
                                             answer_type=Question.NUMBER, order=2)

        question_3 = Question.objects.create(batch=batch, text="Some random question",
                                             answer_type=Question.NUMBER, order=3)
        sub_question_1 = Question.objects.create(batch=batch, text="Specify others", answer_type=Question.TEXT,
                                                 subquestion=True, parent=question_1)

        rule = AnswerRule.objects.create(question=question_1, action=AnswerRule.ACTIONS['ASK_SUBQUESTION'],
                                         condition=AnswerRule.CONDITIONS['EQUALS'],
                                         validate_with_question=question_2, next_question=sub_question_1, batch=batch)

        data = dict(action=rule.action,
                    condition=rule.condition,
                    validate_with_question=rule.validate_with_question, next_question=rule.next_question)

        logic_form = LogicForm(question = question_1, data = data, batch=batch)

        self.assertFalse(logic_form.is_valid())

        another_data = dict(action=rule.action,
                            condition=rule.condition,
                            validate_with_question=question_3.pk)

        logic_form = LogicForm(question = question_1, data = another_data, batch=batch)

        self.assertTrue(logic_form.is_valid())

